from unittest import TestCase
import unittest
from cilantro.storage.contracts import *
from seneca.engine.interface import SenecaInterface


class TestContracts(TestCase):

    def setUp(self):
        with SenecaInterface() as interface:
            interface.r.flushdb()

    def test_seed_contracts_get_code_str(self):
        seed_contracts()
        with SenecaInterface() as interface:
            self.assertTrue(bool(interface.get_code_obj('currency')))
            self.assertTrue(bool(interface.get_code_obj('sample')))

            expected_snipped = 'UNITTEST_FLAG_CURRENCY_SENECA 1729'
            actual_code = interface.get_code_str('currency')
            self.assertTrue(expected_snipped in actual_code)

    def test_seed_contracts_author_info(self):
        seed_contracts()
        with SenecaInterface() as interface:
            contract_metadata = interface.get_contract_meta('currency')
            actual_author = contract_metadata['author']

            self.assertEqual(actual_author, GENESIS_AUTHOR)

    def test_seed_contracts_doesnt_screw_imports_after(self):
        seed_contracts()

        # We should be able to import stuff normally now
        import cilantro
        from collections import OrderedDict
        from cilantro.logger.base import get_logger
        import capnp
        import envelope_capnp

if __name__ == '__main__':
    unittest.main()