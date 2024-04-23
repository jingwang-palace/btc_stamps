import unittest
from pathlib import Path
import sys
from src.stamp import parse_tx_to_stamp_table
import colorlog
import logging
from colour_runner.runner import ColourTextTestRunner

sys.path.append(str(Path(__file__).resolve().parents[1]))

from indexer.tests.src20_variations_data import src20_variations_data
from indexer.tests.db_simulator import DBSimulator

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(asctime)s - %(log_color)s%(levelname)s:%(name)s:%(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }))
logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class TestSrc20Variations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Add the project root directory to the sys.path for module importing
        project_root = Path(__file__).resolve().parent.parent
        sys.path.append(str(project_root))

        # Initialize DB Simulator with the path to dbSimulation.json
        db_simulation_path = project_root / 'indexer' / 'tests' / 'dbSimulation.json'
        cls.db_simulator = DBSimulator(db_simulation_path)

            
    def test_src20_variations(self):
        for test_case in src20_variations_data:
            # stamp_result, src20_result = None, None
            with self.subTest(msg=test_case["description"]):
                additional_params = {
                    "db": self.db_simulator,
                    "tx_hash": test_case["tx_hash"],
                    "source": test_case["source"],
                    "destination": test_case["destination"],
                    "btc_amount": test_case["btc_amount"],
                    "fee": test_case["fee"],
                    "data": test_case['src20JsonString'],
                    "decoded_tx": test_case["decoded_tx"],
                    "keyburn": test_case["keyburn"],
                    "tx_index": test_case["tx_index"],
                    "block_index": test_case["block_index"],
                    "block_time": test_case["block_time"],
                    "is_op_return": test_case["is_op_return"],
                    "valid_stamps_in_block": test_case["valid_stamps_in_block"],
                    "valid_src20_in_block": test_case["valid_src20_in_block"],
                    "p2wsh_data": test_case["p2wsh_data"]
                }
                stamp_result, src20_result = parse_tx_to_stamp_table(**additional_params)
                stamp_result = False if stamp_result is None else stamp_result
                src20_result = False if src20_result is None else src20_result

                self.assertEqual(stamp_result, test_case["expectedOutcome"]["stamp_success"], 
                                msg=f"Failure in stamp_result test: {test_case['expectedOutcome']['message']} - Expected: {test_case['expectedOutcome']['stamp_success']}, Got: {stamp_result}")

                self.assertEqual(src20_result, test_case["expectedOutcome"]["src20_success"], 
                                msg=f"Failure in src20_result test: {test_case['expectedOutcome']['message']} - Expected: {test_case['expectedOutcome']['src20_success']}, Got: {src20_result}")
                
if __name__ == '__main__':
    unittest.main(testRunner=ColourTextTestRunner, exit=False, verbosity=3)