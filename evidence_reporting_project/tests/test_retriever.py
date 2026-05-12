from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_models import KnowledgeCard
from src.retriever import Retriever


class RetrieverTest(unittest.TestCase):
    def test_retrieves_relevant_card(self):
        cards = [
            KnowledgeCard(
                card_id="1",
                title="High DO card",
                trigger_cues=["high_do", "稳定"],
                core_statement="High dissolved oxygen can indicate a well-aerated condition.",
                remarks="",
                source="a.txt",
                source_type="txt",
                chunk_text="High dissolved oxygen with low residual ammonia supports a conservative stable-condition review.",
            ),
            KnowledgeCard(
                card_id="2",
                title="Bulking card",
                trigger_cues=["污泥膨胀"],
                core_statement="Bulking should be reviewed with SV30 and sludge index.",
                remarks="",
                source="b.txt",
                source_type="txt",
                chunk_text="污泥膨胀 usually needs settling review.",
            ),
        ]
        results = Retriever(cards).retrieve("high_do 6.4 stable condition", top_k=1)
        self.assertEqual(results[0].card_id, "1")


if __name__ == "__main__":
    unittest.main()
