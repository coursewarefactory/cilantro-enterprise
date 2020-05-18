from cilantro_ee.nodes.masternode import masternode
from cilantro_ee.nodes import base
from cilantro_ee import router, storage, network
from cilantro_ee.crypto.wallet import Wallet
from cilantro_ee.crypto import canonical
from contracting.db.driver import InMemDriver, ContractDriver
import zmq.asyncio
import asyncio

from unittest import TestCase


def generate_blocks(number_of_blocks):
    previous_hash = '0' * 64
    previous_number = 0

    blocks = []
    for i in range(number_of_blocks):
        new_block = canonical.block_from_subblocks(
            subblocks=[],
            previous_hash=previous_hash,
            block_num=previous_number + 1
        )

        blocks.append(new_block)

        previous_hash = new_block['hash']
        previous_number += 1

    return blocks


async def stop_server(s, timeout):
    await asyncio.sleep(timeout)
    s.stop()


class TestNode(TestCase):
    def setUp(self):
        self.ctx = zmq.asyncio.Context()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.blocks = storage.BlockStorage()

        self.driver = ContractDriver(driver=InMemDriver())
        self.b = masternode.BlockService(
            blocks=self.blocks,
            driver=self.driver
        )

        self.r = router.Router(
            socket_id='tcp://127.0.0.1:18001',
            ctx=self.ctx
        )

        self.r.add_service(base.BLOCK_SERVICE, self.b)

    def tearDown(self):
        self.ctx.destroy()
        self.loop.close()
        self.b.blocks.drop_collections()
        self.b.driver.flush()

    def test_catchup(self):
        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        blocks = generate_blocks(3)

        self.blocks.store_block(blocks[0])
        self.blocks.store_block(blocks[1])
        self.blocks.store_block(blocks[2])
        storage.set_latest_block_height(3, self.driver)

        tasks = asyncio.gather(
            self.r.serve(),
            node.catchup('tcp://127.0.0.1:18001'),
            stop_server(self.r, 1)
        )

        self.loop.run_until_complete(tasks)

        self.assertEqual(storage.get_latest_block_height(node.driver), 3)

    def test_catchup_with_nbn_added(self):
        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        blocks = generate_blocks(4)

        self.blocks.store_block(blocks[0])
        self.blocks.store_block(blocks[1])
        self.blocks.store_block(blocks[2])

        storage.set_latest_block_height(3, self.driver)

        node.new_block_processor.q.append(blocks[3])

        tasks = asyncio.gather(
            self.r.serve(),
            node.catchup('tcp://127.0.0.1:18001'),
            stop_server(self.r, 1)
        )

        self.loop.run_until_complete(tasks)
        self.assertEqual(storage.get_latest_block_height(node.driver), 4)

    def test_should_process_block_false_if_failed_block(self):
        block = {
            'hash': 'f' * 64,
            'number': 1,
            'previous': (b'\x00' * 32).hex(),
            'subblocks': []
        }

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        self.assertFalse(node.should_process(block))

    def test_should_process_block_false_if_current_height_not_increment(self):
        block = {
            'hash': 'a' * 64,
            'number': 2,
            'previous': (b'\x00' * 32).hex(),
            'subblocks': []
        }

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        self.assertFalse(node.should_process(block))

    def test_should_process_block_false_if_previous_if_not_current_hash(self):
        block = {
            'hash': 'a' * 64,
            'number': 1,
            'previous': 'b' * 64,
            'subblocks': []
        }

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        self.assertFalse(node.should_process(block))

    def test_should_process_block_false_if_expected_block_not_equal_to_provided_block(self):
        block = {
            'hash': 'a' * 64,
            'number': 1,
            'previous': (b'\x00' * 32).hex(),
            'subblocks': []
        }

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        self.assertFalse(node.should_process(block))

    def test_should_process_block_true_if_expected_block_equal_to_block(self):
        block = canonical.block_from_subblocks(
            subblocks=[],
            previous_hash='0' * 64,
            block_num=1
        )

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        self.assertTrue(node.should_process(block))

    def test_process_new_block_updates_state(self):
        block = canonical.block_from_subblocks(
            subblocks=[],
            previous_hash='0' * 64,
            block_num=1
        )

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver
        )

        node.process_new_block(block)

        self.assertEqual(storage.get_latest_block_height(node.driver), 1)
        self.assertEqual(storage.get_latest_block_hash(node.driver), block['hash'])

    def test_process_new_block_stores_block_if_should_store(self):
        block = canonical.block_from_subblocks(
            subblocks=[],
            previous_hash='0' * 64,
            block_num=1
        )

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver,
            store=True,
            blocks=self.blocks,
        )

        node.process_new_block(block)

        b = node.blocks.get_block(1)

        self.assertEqual(b, block)

    def test_process_new_block_clears_cache(self):
        block = canonical.block_from_subblocks(
            subblocks=[],
            previous_hash='0' * 64,
            block_num=1
        )

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver,
            store=True,
            blocks=self.blocks,
        )

        node.driver.cache['test'] = 123

        node.process_new_block(block)

        self.assertIsNone(node.driver.cache.get('test'))

    def test_process_new_block_cleans_nbn(self):
        blocks = generate_blocks(2)

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18002',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution={
                'masternodes': [Wallet().verifying_key().hex()],
                'delegates': [Wallet().verifying_key().hex()]
            },
            driver=driver,
            store=True,
            blocks=self.blocks,
        )

        # Add one old and one new block.
        # Function should only delete the old one
        node.new_block_processor.q.append(blocks[0])
        node.new_block_processor.q.append(blocks[1])

        node.process_new_block(blocks[0])

        block = node.new_block_processor.q[0]

        self.assertEqual(block, blocks[1])
        self.assertEqual(len(node.new_block_processor.q), 1)

    def test_start_boots_up_normally(self):
        # This MN will also provide 'catch up' services
        mn_bootnode = 'tcp://127.0.0.1:18001'
        mn_wallet = Wallet()
        mn_network = network.Network(
            wallet=mn_wallet,
            ip_string=mn_bootnode,
            ctx=self.ctx,
            router=self.r
        )

        blocks = generate_blocks(4)

        self.blocks.store_block(blocks[0])
        self.blocks.store_block(blocks[1])
        self.blocks.store_block(blocks[2])

        storage.set_latest_block_height(3, self.driver)

        dl_bootnode = 'tcp://127.0.0.1:18002'
        dl_wallet = Wallet()
        dl_router = router.Router(
                socket_id=dl_bootnode,
                ctx=self.ctx
            )
        dl_network = network.Network(
            wallet=dl_wallet,
            ip_string=dl_bootnode,
            ctx=self.ctx,
            router=dl_router
        )

        constitution = {
            'masternodes': [mn_wallet.verifying_key().hex()],
            'delegates': [dl_wallet.verifying_key().hex()]
        }

        driver = ContractDriver(driver=InMemDriver())
        node = base.Node(
            socket_base='tcp://127.0.0.1:18003',
            ctx=self.ctx,
            wallet=Wallet(),
            constitution=constitution,
            driver=driver,
            store=False,
        )

        bootnodes = [mn_bootnode, dl_bootnode]
        vks = [mn_wallet.verifying_key().hex(), dl_wallet.verifying_key().hex()]

        tasks = asyncio.gather(
            self.r.serve(),
            dl_router.serve(),
            mn_network.start(bootnodes, vks),
            dl_network.start(bootnodes, vks),
            stop_server(self.r, 0.2),
            stop_server(dl_router, 0.2),
        )

        self.loop.run_until_complete(tasks)

        tasks = asyncio.gather(
            self.r.serve(),
            dl_router.serve(),
            node.start([mn_bootnode, dl_bootnode]),
            stop_server(self.r, 1),
            stop_server(dl_router, 1),
            stop_server(node.router, 1)
        )

        self.loop.run_until_complete(tasks)

        self.assertEqual(storage.get_latest_block_height(node.driver), 3)
        self.assertEqual(storage.get_latest_block_hash(node.driver), blocks[2]['hash'])

