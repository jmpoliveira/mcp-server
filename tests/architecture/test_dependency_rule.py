"""Enforces the Clean Architecture dependency rule by inspecting imports."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

# layer -> import prefixes it must NOT use
FORBIDDEN = {
    "domain": (
        "src.application",
        "src.infrastructure",
        "src.interface",
        "mcp",
        "pydantic",
        "starlette",
    ),
    "application": (
        "src.infrastructure",
        "src.interface",
        "mcp",
        "pydantic",
        "starlette",
    ),
    "infrastructure": ("src.interface",),
    "interface": ("src.infrastructure",),
}


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def violations(layer: str) -> list[str]:
    found: list[str] = []
    for path in (SRC / layer).rglob("*.py"):
        for module in imported_modules(path):
            for prefix in FORBIDDEN[layer]:
                if module == prefix or module.startswith(prefix + "."):
                    found.append(f"{path.relative_to(SRC)} imports {module}")
    return found


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_respects_the_dependency_rule(layer):
    assert violations(layer) == []
