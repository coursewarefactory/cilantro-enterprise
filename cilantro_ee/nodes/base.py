from cilantro_ee import storage, network, router, authentication, rewards, upgrade
from cilantro_ee.crypto import canonical
from cilantro_ee.contracts import sync
from contracting.db.driver import ContractDriver
import cilantro_ee
import zmq.asyncio
import asyncio

from contracting.client import ContractingClient

from cilantro_ee.logger.base import get_logger
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

BLOCK_SERVICE = 'service'
NEW_BLOCK_SERVICE = 'new_blocks'
WORK_SERVICE = 'work'
CONTENDER_SERVICE = 'contenders'

GET_BLOCK = 'get_block'
GET_HEIGHT = 'get_height'


async def get_latest_block_height(ip_string: str, ctx: zmq.asyncio.Context):
    msg = {
        'name': GET_HEIGHT,
        'arg': ''
    }

    response = await router.request(
        socket_str=ip_string,
        service=BLOCK_SERVICE,
        msg=msg,
        ctx=ctx
    )

    return response


async def get_block(block_num: int, ip_string: str, ctx: zmq.asyncio.Context):
    msg = {
        'name': GET_BLOCK,
        'arg': block_num
    }

    response = await router.request(
        socket_str=ip_string,
        service=BLOCK_SERVICE,
        msg=msg,
        ctx=ctx
    )

    return response


class NewBlock(router.Processor):
    def __init__(self, driver: ContractDriver):
        self.q = []
        self.driver = driver
        self.log = get_logger('NBN')

    async def process_message(self, msg):
        self.q.append(msg)

    async def wait_for_next_nbn(self):
        while len(self.q) <= 0:
            await asyncio.sleep(0)

        nbn = self.q.pop(0)

        self.q.clear()

        return nbn

    def clean(self):
        num = storage.get_latest_block_height(self.driver)
        self.q = [nbn for nbn in self.q if nbn['number'] >= num]


class Node:
    def __init__(self, socket_base, ctx: zmq.asyncio.Context, wallet, constitution: dict,
                 blocks=None, bootnodes=[], driver=ContractDriver(), debug=True, store=False):

        self.driver = driver
        self.nonces = storage.NonceStorage()
        self.store = store

        self.blocks = blocks

        if self.store:
            self.blocks = storage.BlockStorage()

        self.log = get_logger('NODE')
        self.log.propagate = debug
        self.socket_base = socket_base
        self.wallet = wallet
        self.ctx = ctx

        self.client = ContractingClient(
            driver=self.driver,
            submission_filename=cilantro_ee.contracts.__path__[0] + '/submission.s.py'
        )

        self.bootnodes = bootnodes
        self.constitution = constitution

        sync.setup_genesis_contracts(
            initial_masternodes=self.constitution['masternodes'],
            initial_delegates=self.constitution['delegates'],
            client=self.client
        )

        self.socket_authenticator = authentication.SocketAuthenticator(ctx=self.ctx, client=self.client)

        self.upgrade_manager = upgrade.UpgradeManager(client=self.client)

        self.router = router.Router(
            socket_id=socket_base + '18000',
            ctx=self.ctx
        )

        self.network = network.Network(
            wallet=wallet,
            ip_string=socket_base + '18000',
            ctx=self.ctx,
            router=self.router
        )

        self.new_block_processor = NewBlock(driver=self.driver)
        self.router.add_service(NEW_BLOCK_SERVICE, self.new_block_processor)

        self.running = False

    async def catchup(self, mn_seed):
        # Get the current latest block stored and the latest block of the network
        current = storage.get_latest_block_height(self.driver)
        latest = await get_latest_block_height(ip_string=mn_seed, ctx=self.ctx)

        assert type(latest) != dict, 'Provided node is not in sync.'

        self.log.info(f'Current: {current}, Latest: {latest}')

        # Increment current by one. Don't count the genesis block.
        if current == 0:
            current = 1

        # Find the missing blocks process them
        for i in range(current, latest + 1):
            block = await get_block(block_num=i, ip_string=mn_seed, ctx=self.ctx)
            self.update_state(block)

        # Process any blocks that were made while we were catching up
        while len(self.new_block_processor.q) > 0:
            block = self.new_block_processor.q.pop(0)
            self.update_state(block)

    def should_process(self, block):
        # Test if block failed immediately
        if block['hash'] == 'f' * 64:
            return False

        # Get current metastate
        current_hash = storage.get_latest_block_hash(self.driver)
        current_height = storage.get_latest_block_height(self.driver)

        # Test if block contains the same metastate
        if block['number'] != current_height + 1:
            return False

        if block['previous'] != current_hash:
            return False

        # If so, use metastate and subblocks to create the 'expected' block
        expected_block = canonical.block_from_subblocks(
            subblocks=block['subblocks'],
            previous_hash=current_hash,
            block_num=current_height + 1
        )

        # Return if the block contains the expected information
        return block == expected_block

    def update_state(self, block):
        # Check if the block is valid
        if self.should_process(block):
            # Commit the state changes and nonces to the database
            storage.update_state_with_block(
                block=block,
                driver=self.driver,
                nonces=self.nonces
            )

            # Calculate and issue the rewards for the governance nodes
            rewards.issue_rewards(
                block=block,
                client=self.client
            )

    def process_new_block(self, block):
        self.log.info('Processing new block...')

        # Update the state and refresh the sockets so new nodes can join
        self.update_state(block)
        self.socket_authenticator.refresh_governance_sockets()

        # Store the block if it's a masternode
        if self.store:
            self.blocks.store_block(block)

        # Prepare for the next block by flushing out driver and notification state
        self.driver.clear_pending_state()
        self.new_block_processor.clean()

        # Finally, check and initiate an upgrade if one needs to be done
        self.upgrade_manager.version_check()

    async def start(self, bootnodes):
        # Get the set of VKs we are looking for from the constitution argument
        vks = self.constitution['masternodes'] + self.constitution['delegates']

        # Use it to boot up the network
        await self.network.start(bootnodes=bootnodes, vks=vks)

        # Take a masternode vk from the constitution and look up its IP
        masternode = self.constitution['masternodes'][0]
        masternode_ip = self.network.peers[masternode]

        # Use this IP to request any missed blocks
        await self.catchup(mn_seed=masternode_ip)

        # Refresh the sockets to accept new nodes
        self.socket_authenticator.refresh_governance_sockets()

        # Start running
        self.running = True

    def stop(self):
        # Kill the router and throw the running flag to stop the loop
        self.router.stop()
        self.running = False

    def _get_member_peers(self, contract_name):
        members = self.client.get_var(
            contract=contract_name,
            variable='S',
            arguments=['members']
        )

        member_peers = dict()

        for member in members:
            ip = self.network.peers.get(member)
            if ip is not None:
                member_peers[member] = ip

        return member_peers

    def get_delegate_peers(self):
        return self._get_member_peers('delegates')

    def get_masternode_peers(self):
        return self._get_member_peers('masternodes')


def get_genesis_block():
    block = {
        'hash': (b'\x00' * 32).hex(),
        'number': 0,
        'previous': (b'\x00' * 32).hex(),
        'subblocks': []
    }
    return block
