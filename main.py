import argparse
import os
import sys
import urllib.request
import gzip
import tarfile
import io


def validate_args(args):
    errors = []
    if not args.package:
        errors.append("Empty name")
    if not args.repo:
        errors.append("Empty path")
    else:
        if args.mode == "online":
            if not (
                args.repo.startswith("http://") or args.repo.startswith("https://")
            ):
                errors.append("URL must start with http:// or https:// in online mode")
    if args.mode not in ["online", "test"]:
        errors.append(f"{args.mode} mode not exist")
    if not args.version:
        errors.append("Empty version")
    if not args.output:
        errors.append("Empty output name")
    if args.depth <= 0:
        errors.append("Depth incorrect")
    return errors


def download_apkindex(repo_url):
    try:
        if not repo_url.endswith("/"):
            repo_url += "/"
        apkindex_url = repo_url + "APKINDEX.tar.gz"

        print(f"Downloading APKINDEX from: {apkindex_url}")

        with urllib.request.urlopen(apkindex_url) as response:
            apkindex_data = response.read()

        with tarfile.open(fileobj=io.BytesIO(apkindex_data), mode="r:gz") as tar:
            apkindex_file = tar.extractfile("APKINDEX")
            if apkindex_file:
                content = apkindex_file.read().decode("utf-8")
                return parse_apkindex(content)
            else:
                print("APKINDEX file not found in archive")
                return {}

    except Exception as e:
        print(f"Error downloading APKINDEX: {e}")
        return {}


def parse_apkindex(content):
    packages = {}
    current_pkg = {}

    for line in content.split("\n"):
        if line.strip() == "":
            if current_pkg and "P" in current_pkg:
                pkg_name = current_pkg["P"]
                packages[pkg_name] = {
                    "version": current_pkg.get("V", ""),
                    "dependencies": parse_dependencies(current_pkg.get("D", "")),
                    "description": current_pkg.get("T", ""),
                }
            current_pkg = {}
        else:
            if ":" in line:
                key, value = line.split(":", 1)
                current_pkg[key] = value

    return packages


def parse_dependencies(dep_string):
    if not dep_string:
        return []

    dependencies = []
    for dep in dep_string.split():
        dep = dep.split(">")[0].split("<")[0].split("=")[0]
        if dep.startswith("so:"):
            continue
        if dep not in dependencies:
            dependencies.append(dep)

    return dependencies


def get_package_dependencies(package_name, version, packages_data):
    if package_name not in packages_data:
        return None

    package_info = packages_data[package_name]

    if version != "latest" and package_info["version"] != version:
        print(f"Warning: Version {version} not found, using {package_info['version']}")

    return package_info["dependencies"]


def main():
    parser = argparse.ArgumentParser(description="Dependency graph visualizer")

    parser.add_argument("--package", required=True, help="Package name")
    parser.add_argument(
        "--repo", required=True, help="Repository URL or test file path"
    )
    parser.add_argument(
        "--mode",
        default="online",
        choices=["online", "test"],
        help="Mode: online or test",
    )
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

    print("\nStage 2: Getting direct dependencies")

    packages_data = {}

    if args.mode == "online":
        packages_data = download_apkindex(args.repo)
    else:
        print("Test mode - using sample data")
        packages_data = {
            "nginx": {
                "version": "1.20.1",
                "dependencies": ["pcre", "zlib", "openssl"],
                "description": "NGINX web server",
            },
            "pcre": {
                "version": "8.45",
                "dependencies": ["libc", "libstdc++"],
                "description": "Perl Compatible Regular Expressions",
            },
        }

    dependencies = get_package_dependencies(args.package, args.version, packages_data)

    if dependencies is None:
        print(f"Package {args.package} not found in repository")
        sys.exit(1)

    print(f"Direct dependencies for {args.package}:")
    for dep in dependencies:
        print(f"  - {dep}")


if __name__ == "__main__":
    main()
