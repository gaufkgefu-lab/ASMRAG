from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.knowledge_card_builder import build_knowledge_cards


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="D:/python/zhishiku")
    parser.add_argument("--output", default="data/knowledge_base/knowledge_cards.jsonl")
    args = parser.parse_args()
    cards = build_knowledge_cards(args.input_dir, args.output)
    print(f"Built {len(cards)} knowledge cards -> {args.output}")


if __name__ == "__main__":
    main()
