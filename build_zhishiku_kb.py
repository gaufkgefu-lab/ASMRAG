from pathlib import Path
import subprocess
import sys


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    source_dir = base_dir / "zhishiku"
    output_dir = base_dir / "zhishiku_kb"
    script = base_dir / "vector_kb.py"

    command = [
        sys.executable,
        str(script),
        "build",
        "--source",
        str(source_dir),
        "--output",
        str(output_dir),
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
