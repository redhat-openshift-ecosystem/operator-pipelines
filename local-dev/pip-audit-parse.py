#!/usr/bin/env python3
import json
import argparse
from typing import Dict, Any

from rich.table import Table
from rich.console import Console


def parse_vulnerabilities_json(data: Dict[str, Any]) -> bool:
    """
    Parses pip-audit json output, extracts fixable vulnerabilities
    and pretty prints them.
    """

    vulnerable_packages = []
    for package in data.get("dependencies", {}):
        name = package.get("name")
        vulnerabilities = package.get("vulns", [])
        version = package.get("version")
        if not vulnerabilities:
            print(f"✅ {name} {version}")
        else:
            has_fixable_vulnerabilities = False
            for vulnerability in vulnerabilities:
                # filter out vulnerabilities that cannot be fixed
                if fix := vulnerability.get("fix_versions", []) or None:
                    vulnerable_packages.append(
                        {
                            "name": name,
                            "version": version,
                            "vulnerability": vulnerability.get("id"),
                            "fix": fix,
                        }
                    )
                    has_fixable_vulnerabilities = True
            if has_fixable_vulnerabilities:
                print(f"❌ {name} {version}")
            else:
                print(f"❗ {name} {version}")

    if vulnerable_packages:
        print("Vulnerable packages found:")
        table = Table("Package", "Version", "Vulnerability", "Fixed version")
        to_update = set()
        for package in vulnerable_packages:
            table.add_row(
                package["name"],
                package["version"],
                package["vulnerability"],
                ",".join(package["fix"]),
            )
            to_update.add(package["name"])
        console = Console()
        console.print(table)
        print(f"To fix, run:\npoetry update {' '.join(to_update)} --update-reuse")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a JSON file.")
    parser.add_argument("filename", help="The JSON file to process")

    args = parser.parse_args()
    with open(args.filename, "r") as file:
        data = json.load(file)

    if not parse_vulnerabilities_json(data):
        exit(1)


if __name__ == "__main__":
    main()
