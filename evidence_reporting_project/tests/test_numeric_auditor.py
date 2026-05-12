from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_models import GeneratedReport
from src.numeric_auditor import audit_report


class NumericAuditorTest(unittest.TestCase):
    def test_audit_passes_for_matching_values(self):
        report = GeneratedReport(
            report_id="r1",
            date="20220603",
            mode="A",
            method="rag",
            llm_provider="mock",
            report_metadata={},
            monitoring_summary="",
            diagnostic_analysis="",
            microbiology_settling_evidence="",
            follow_up_actions=[],
            limitations=[],
            auditable_statements={"do": 6.47, "cod": 21.26},
        )
        result = audit_report(report, {"do": 6.47, "cod": 21.26})
        self.assertTrue(result.report_level_pass)
        self.assertAlmostEqual(result.audit_consistency, 1.0)


if __name__ == "__main__":
    unittest.main()
