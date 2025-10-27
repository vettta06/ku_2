import argparse
import os
import sys


def validate_args(args):
    errors = []
    if not args.package:
        errors.append("Empty name")
    if not args.repo:
        errors.append("Empty path")
    else:
        if not (args.repo.startswith("http://") or args.repo.startswith("https://") or os.path.isfile(args.repo)):
            errors.append("Path not exist")
    if args.mode not in ["online", "test"]:
        errors.append(f"{args.mode} mode not exist")
    if not args.version:
        errors.append("Empty version")
    if not args.output:
        errors.append("Empty output name")
    if args.depth <= 0:
        errors.append("Depth incorrect")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Dependency graph visualizer")

    parser.add_argument("--package", required=True, help="Package name")
    parser.add_argument("--repo", required=True, help="Repository URL or test file path")
    parser.add_argument("--mode", default="online", choices=["online", "test"], help="Mode: online or test")
    parser.add_argument("--version", default="latest", help="Package version")
    parser.add_argument("--output", default="graph.svg", help="Output image file name")
    parser.add_argument("--depth", type=int, default=3, help="Max dependency depth")

    args = parser.parse_args()
    errors = validate_args(args)
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

    print(f"package: {args.package}")
    print(f"repo: {args.repo}")
    print(f"mode: {args.mode}")
    print(f"version: {args.version}")
    print(f"output: {args.output}")
    print(f"depth: {args.depth}")


if __name__ == "__main__":
    main()
