from __future__ import annotations

import re
from pathlib import Path


def resolve_prompt(
    name: str,
    branch: str,
    iteration: int,
    base_dir: Path = Path("."),
) -> str:
    """Resolve a prompt file by name using precedence: iteration -> branch -> root prompts/.

    The name should be the filename without extension (e.g. "system", "user", "idle").
    """
    filename = f"{name}.txt"

    candidates = [
        base_dir / "experiments" / branch / str(iteration) / "prompts" / filename,
        base_dir / "experiments" / branch / "prompts" / filename,
        base_dir / "prompts" / filename,
    ]

    for path in candidates:
        if path.exists():
            return path.read_text()

    raise FileNotFoundError(
        f"Prompt '{name}' not found. Searched: {[str(p) for p in candidates]}"
    )


def fill_template(template: str, variables: dict[str, str | int | float]) -> str:
    """Fill placeholder variables in a prompt template.

    Uses {variable_name} syntax. Missing variables are left as-is.
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result
