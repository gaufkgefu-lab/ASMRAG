from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_models import DayRecord
from src.prompt_builder import build_prompt


class PromptBuilderTest(unittest.TestCase):
    def test_prompt_contains_primary_basis(self):
        record = DayRecord(
            date="20220603",
            same_day_primary_evidence={"reference_table": {"do": 6.47}},
            optional_biological_evidence=None,
            optional_visual_evidence={"status": "not_implemented"},
        )
        prompt, path = build_prompt("A", "direct", record, [])
        self.assertIn("primary basis", prompt.lower())
        self.assertTrue(path.endswith("mode_a_direct.txt"))


if __name__ == "__main__":
    unittest.main()
