import argparse
import os
import sys
import urllib.request
import gzip
import tarfile
import io
from collections import deque


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
        print(f"Version {version} not found, using {package_info['version']}")

    return package_info["dependencies"]


def build_dependency_graph(package_name, version, packages_data, max_depth):
    graph = {}
    visited = set()
    queue = deque()
    queue.append((package_name, version, 0))
    visited.add(package_name)
    while queue:
        cur_pkg, cur_ver, depth = queue.popleft()
        if depth >= max_depth:
            continue
        dependencies = get_package_dependencies(cur_pkg, cur_ver, packages_data)
        if dependencies is None:
            continue
        graph[cur_pkg] = dependencies
        for dep in dependencies:
            if dep not in visited and dep in packages_data:
                visited.add(dep)
                queue.append((dep, packages_data[dep]['version'], depth + 1))
            elif dep not in packages_data:
                graph.setdefault(cur_pkg, []).append(dep)
    return graph


def parse_file_test(file_path):
    packages = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ':' in line:
                    pkg_name, deps = line.split(':', 1)
                    pkg_name = pkg_name.strip()
                    dependencies = [d.strip() for d in deps.split() if d.strip()]
                    packages[pkg_name] = {
                        'version': '1.0',
                        'dependencies': dependencies,
                        'description': f'Test package {pkg_name}'
                    }
    except Exception as e:
        print(f"Error reading test file {e}")
    return packages


def detect_cycles(graph):
    def dfs(node, path):
        if node in path:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return None
        visited.add(node)
        path.append(node)
        for neigh in graph.get(node, []):
            cycle_dfs = dfs(neigh, path.copy())
            if cycle_dfs:
                return cycle_dfs
        return None

    visited = set()
    for node in graph:
        if node not in visited:
            cycle = dfs(node, [])
            if cycle:
                return cycle
    return None


def print_dependency_graph(graph, root_package):
    print(f"\nDependency graph for {root_package}:")

    def print_deps(node, depth, visited):
        if node in visited:
            indent = "  " * depth
            print(f"{indent}{node} [CYCLE]")
            return

        visited.add(node)
        indent = "  " * depth
        print(f"{indent}{node}")

        if node in graph:
            for child in graph[node]:
                print_deps(child, depth + 1, visited.copy())

    print_deps(root_package, 0, set())


def topological_sort(graph):
    if not graph:
        return [], False
    inv_graph = {node: [] for node in graph}
    for package in graph:
        for dep in graph[package]:
            if dep in graph:
                inv_graph[dep].append(package)
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for dep in inv_graph[node]:
            in_degree[dep] += 1
    queue = deque([node for node in graph if in_degree[node] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for dep in inv_graph[node]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
    has_cycle = len(order) != len(graph)
    return order, has_cycle


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
    print(f"\nStage 3: Building dependency graph (max depth: {args.depth}) ===")
    packages_data = {}

    if args.mode == "online":
        packages_data = download_apkindex(args.repo)
    else:
        packages_data = parse_file_test(args.repo)
        if not  packages_data:
            print("Using fallback test data")
            packages_data = {
                "A": {"version": "1.0", "dependencies": ["B", "C"], "description": "Package A"},
                "B": {"version": "2.0", "dependencies": ["D"], "description": "Package B"},
                "C": {"version": "3.0", "dependencies": ["D", "E"], "description": "Package C"},
                "D": {"version": "4.0", "dependencies": [], "description": "Package D"},
                "E": {"version": "5.0", "dependencies": ["A"], "description": "Package E"}
            }
    dependency_graph = build_dependency_graph(args.package, args.version, packages_data, args.depth)
    print(f"\nDependencies for {args.package}:")
    dependencies = get_package_dependencies(args.package, args.version, packages_data)
    if dependencies:
        for dep in dependencies:
            print(f"   - {dep}")
    else:
        print("  No dependencies")
    print_dependency_graph(dependency_graph, args.package)
    cycle = detect_cycles(dependency_graph)
    if cycle:
        print(f"\nCycle detected: {' -> '.join(cycle)}")
    else:
        print("\nNo cycles detected")

    print(f"\nStage 4: Load order for {args.package} ===")
    load_order, has_cycle = topological_sort(dependency_graph)
    if has_cycle:
        print("Graph contains cycles, load order may be incomplete")
    if not load_order:
        print("No valid load order can be determined due to cycles")
    else:
        print("Load order: ")
        for i, package in enumerate(load_order, 1):
            print(f"{i}. {package}")

if __name__ == "__main__":
    main()
