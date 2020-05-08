from contracting.execution.executor import Executor
from contracting.stdlib.bridge.time import Datetime
from contracting.db.encoder import encode, decode, safe_repr
from cilantro_ee.crypto.canonical import tx_hash_from_tx, format_dictionary
from cilantro_ee.crypto.merkle_tree import merklize
from cilantro_ee.logger.base import get_logger
from datetime import datetime
import hashlib
import heapq


log = get_logger('EXE')


def execute_tx(executor: Executor, transaction, stamp_cost, environment: dict={}):
    # Deserialize Kwargs. Kwargs should be serialized JSON moving into the future for DX.

    output = executor.execute(
        sender=transaction['payload']['sender'],
        contract_name=transaction['payload']['contract'],
        function_name=transaction['payload']['function'],
        stamps=transaction['payload']['stamps_supplied'],
        stamp_cost=stamp_cost,
        kwargs=transaction['payload']['kwargs'],
        environment=environment,
        auto_commit=False
    )

    tx_hash = tx_hash_from_tx(transaction)

    tx_output = {
        'hash': tx_hash,
        'transaction': transaction,
        'status': output['status_code'],
        'state': output['writes'],
        'stamps_used': output['stamps_used'],
        'result': safe_repr(output['result'])
    }

    tx_output = format_dictionary(tx_output)

    executor.driver.pending_writes.clear() # add

    return tx_output


def generate_environment(driver, timestamp, input_hash):
    now = Datetime._from_datetime(
        datetime.utcfromtimestamp(timestamp/1000)
    )

    return {
        'block_hash': driver.latest_block_hash,
        'block_num': driver.latest_block_num + 1,
        '__input_hash': input_hash,  # Used for deterministic entropy for random games
        'now': now
    }


def execute_tx_batch(executor, driver, batch, timestamp, input_hash, stamp_cost):
    environment = generate_environment(driver, timestamp, input_hash)

    # Each TX Batch is basically a subblock from this point of view and probably for the near future
    tx_data = []
    for transaction in batch['transactions']:
        tx_data.append(execute_tx(executor=executor,
                                  transaction=transaction,
                                  environment=environment,
                                  stamp_cost=stamp_cost)
                       )

    return tx_data


def execute_work(executor, driver, work, wallet, previous_block_hash, stamp_cost, parallelism=4):
    # Assume single threaded, single process for now.
    subblocks = []
    i = 0

    while len(work) > 0:
        _, tx_batch = heapq.heappop(work)

        results = execute_tx_batch(
            executor=executor,
            driver=driver,
            batch=tx_batch,
            timestamp=tx_batch['timestamp'],
            input_hash=tx_batch['input_hash'],
            stamp_cost=stamp_cost
        )

        if len(results) > 0:
            merkle = merklize([encode(r).encode() for r in results])
            proof = wallet.sign(merkle[0])
        else:
            merkle = merklize([bytes.fromhex(tx_batch['input_hash'])])
            proof = wallet.sign(bytes.fromhex(tx_batch['input_hash']))

        merkle_tree = {
            'leaves': merkle,
            'signature': proof.hex()
        }

        sbc = {
            'input_hash': tx_batch['input_hash'],
            'transactions': results,
            'merkle_tree': merkle_tree,
            'signer': wallet.verifying_key().hex(),
            'subblock': i % parallelism,
            'previous_block_hash': previous_block_hash
        }

        sbc = format_dictionary(sbc)

        subblocks.append(sbc)
        i += 1

    return subblocks
