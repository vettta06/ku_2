import argparse


def main():
    parser = argparse.ArgumentParser(description="Dependency graph visualizer")

    parser.add_argument("--package", required=True, help="Package name")
    parser.add_argument("--repo", required=True, help="Repository URL or test file path")
    parser.add_argument("--mode", default="online", choices=["online", "test"], help="Mode: online or test")
    parser.add_argument("--version", default="latest", help="Package version")
    parser.add_argument("--output", default="graph.svg", help="Output image file name")
    parser.add_argument("--depth", type=int, default=3, help="Max dependency depth")

    args = parser.parse_args()

    print(f"package: {args.package}")
    print(f"repo: {args.repo}")
    print(f"mode: {args.mode}")
    print(f"version: {args.version}")
    print(f"output: {args.output}")
    print(f"depth: {args.depth}")


if __name__ == "__main__":
    main()
