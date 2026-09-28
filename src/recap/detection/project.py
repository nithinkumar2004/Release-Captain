from pathlib import Path

MARKERS: dict[str, tuple[str, ...]] = {
    "Python": ("pyproject.toml", "setup.py", "requirements.txt"),
    "Node.js": ("package.json",),
    "Rust": ("Cargo.toml",),
    "Go": ("go.mod",),
    ".NET": ("*.sln", "*.csproj", "*.fsproj"),
}


def detect_project(root: Path) -> str:
    matches = [
        name
        for name, patterns in MARKERS.items()
        if any(next(root.glob(pattern), None) is not None for pattern in patterns)
    ]
    if not matches:
        return "Unknown"
    if len(matches) > 1:
        return "Multiple: " + ", ".join(sorted(matches))
    return matches[0]
