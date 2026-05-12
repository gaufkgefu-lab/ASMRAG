from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import run_reporting_pipeline


class PipelineSmokeTest(unittest.TestCase):
    def test_mode_a_smoke(self):
        result = run_reporting_pipeline("20220603", "A", method="rag", llm_provider="mock", top_k=3)
        self.assertEqual(result["report"].mode, "A")
        self.assertTrue(result["audit"].report_level_pass)


if __name__ == "__main__":
    unittest.main()
