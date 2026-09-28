from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from recap.core.models import CheckResult

REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
GO_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9._/-]+)\s+(v[0-9][^\s]*)")


def analyze_dependencies(root: Path) -> CheckResult:
    declarations: list[str] = []
    manifests = 0
    try:
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            manifests += 1
            parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = parsed.get("project", {})
            declarations.extend(_requirements(project.get("dependencies", [])))
            optional = project.get("optional-dependencies", {})
            if isinstance(optional, dict):
                for group in optional.values():
                    declarations.extend(_requirements(group))
        requirements = root / "requirements.txt"
        if requirements.is_file():
            manifests += 1
            for line in requirements.read_text(encoding="utf-8").splitlines():
                item = line.split("#", 1)[0].strip()
                if not item or item.startswith("-"):
                    continue
                match = REQUIREMENT_NAME.match(item)
                if match:
                    declarations.append(match.group(1))
        package_json = root / "package.json"
        if package_json.is_file():
            manifests += 1
            parsed_json = json.loads(package_json.read_text(encoding="utf-8"))
            if not isinstance(parsed_json, dict):
                raise ValueError("package.json root must be an object.")
            for section in ("dependencies", "devDependencies", "optionalDependencies"):
                values = parsed_json.get(section, {})
                if isinstance(values, dict):
                    declarations.extend(str(name) for name in values)
        cargo = root / "Cargo.toml"
        if cargo.is_file():
            manifests += 1
            parsed_cargo = tomllib.loads(cargo.read_text(encoding="utf-8"))
            for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                values = parsed_cargo.get(section, {})
                if isinstance(values, dict):
                    declarations.extend(str(name) for name in values)
        go_mod = root / "go.mod"
        if go_mod.is_file():
            manifests += 1
            for line in go_mod.read_text(encoding="utf-8").splitlines():
                match = GO_REQUIREMENT.match(line)
                if match:
                    declarations.append(match.group(1))
        for csproj in (*root.glob("*.csproj"), *root.glob("*.fsproj")):
            manifests += 1
            xml_root = ET.parse(csproj).getroot()
            for package in xml_root.iter():
                if package.tag.rsplit("}", 1)[-1] == "PackageReference":
                    name = package.attrib.get("Include")
                    if name:
                        declarations.append(name)
    except (
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        ET.ParseError,
        tomllib.TOMLDecodeError,
    ) as exc:
        return CheckResult(
            "dependencies",
            "failed",
            f"Dependency manifest could not be analyzed ({exc.__class__.__name__}).",
        )
    unique = sorted(set(declarations), key=str.casefold)
    if not manifests:
        return CheckResult("dependencies", "skipped", "No supported dependency manifests found.")
    details = unique[:100]
    if len(unique) > 100:
        details.append(f"... and {len(unique) - 100} more")
    return CheckResult(
        "dependencies",
        "passed",
        f"Inventoried {len(unique)} declared dependencies across {manifests} manifest(s); no vulnerability database was queried.",
        details,
    )


def _requirements(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for declaration in value:
        match = REQUIREMENT_NAME.match(str(declaration))
        if match:
            names.append(match.group(1))
    return names
