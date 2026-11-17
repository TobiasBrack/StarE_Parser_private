"""Parse STARe text files in a directory into JSON beside each source file."""

import argparse
import sys
from pathlib import Path

from stare_parser import parse_file, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory to search recursively")
    args = parser.parse_args(argv)

    if not args.directory.is_dir():
        parser.error(f"not a directory: {args.directory}")

    files = sorted(args.directory.rglob("*.txt"))
    if not files:
        print(f"No .txt files found in {args.directory}", file=sys.stderr)
        return 1

    failed = 0
    for path in files:
        try:
            parsed = parse_file(path)
            write_json(parsed, path.with_suffix(".json"))
        except (OSError, ValueError) as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            failed += 1
            continue
        for warning in parsed["warnings"]:
            print(f"WARN {path}: {warning}", file=sys.stderr)
        print(f"{path} -> {path.with_suffix('.json')}")

    print(f"{len(files) - failed}/{len(files)} files parsed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
