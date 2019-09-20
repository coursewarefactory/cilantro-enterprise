from cilantro_ee.protocol.transaction import TransactionBuilder, verify_packed_tx
from unittest import TestCase
from cilantro_ee.protocol.wallet import Wallet
import os
from cilantro_ee.messages import capnp as schemas

import capnp
transaction_capnp = capnp.load(os.path.dirname(schemas.__file__) + '/transaction.capnp')


class TestContractTransaction(TestCase):
    def test_init(self):
        TransactionBuilder('blah', 123, 'blah', 'blah', 'blah', {'something': 123})

    def test_signing_flips_true(self):
        w = Wallet()
        tx = TransactionBuilder(w.verifying_key().hex(),
                                1000000, 'currency', 'transfer', 'test',
                                {'amount': 123})

        self.assertFalse(tx.tx_signed)

        tx.sign(w.signing_key().hex())

        self.assertTrue(tx.tx_signed)

    def test_generate_proof_flips_true(self):
        w = Wallet()
        tx = TransactionBuilder(w.verifying_key().hex(),
                                1000000, 'currency', 'transfer', 'test',
                                {'amount': 123})

        self.assertFalse(tx.proof_generated)

        tx.generate_proof()

        self.assertTrue(tx.proof_generated)

    def test_serialize_if_not_signed_returns_none(self):
        w = Wallet()
        tx = TransactionBuilder(w.verifying_key().hex(),
                                1000000, 'currency', 'transfer', 'test',
                                {'amount': 123})

        self.assertIsNone(tx.serialize())

    def test_serialize_returns_bytes(self):
        w = Wallet()
        tx = TransactionBuilder(w.verifying_key().hex(),
                                1000000, 'currency', 'transfer', 'test',
                                {'amount': 123})

        tx.sign(w.signing_key().hex())

        tx_packed = tx.serialize()

        self.assertTrue(verify_packed_tx(w.verifying_key(), tx_packed))

    def test_bad_bytes_returns_false_on_verify(self):
        w = Wallet()
        b = b'bad'
        self.assertFalse(verify_packed_tx(w.verifying_key(), b))

    def test_passing_float_in_contract_kwargs_raises_assertion(self):
        w = Wallet()
        with self.assertRaises(AssertionError):
            TransactionBuilder(w.verifying_key().hex(),
                               1000000, 'currency', 'transfer', 'test',
                               {'amount': 123.00})

    def test_passing_non_supported_type_in_contract_kwargs_raises_assertion(self):
        w = Wallet()
        with self.assertRaises(AssertionError):
            TransactionBuilder(w.verifying_key().hex(),
                               1000000, 'currency', 'transfer', 'test',
                               {'amount': ['b']})