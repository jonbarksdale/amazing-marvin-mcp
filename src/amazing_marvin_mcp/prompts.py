# ABOUTME: Loads MCP prompts from markdown files in the prompts/ directory.
# ABOUTME: Each .md file becomes a registered prompt; first line is the description.

from collections.abc import Callable
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(path: Path) -> tuple[str, str]:
    """Parse a prompt markdown file into (description, body).

    The first line is the description. A blank line separates it from the body.
    Raises ValueError if no blank line separator is found.
    """
    text = path.read_text()
    lines = text.split("\n")
    description = lines[0].strip()
    # Find first blank line separator
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "":
            body = "\n".join(lines[i + 1 :]).strip()
            return description, body
    msg = f"Prompt file {path.name} must have a blank line between description and body."
    raise ValueError(msg)


def _make_prompt(text: str) -> Callable[[], str]:
    """Create a closure that returns the given prompt text."""

    def prompt_fn() -> str:
        return text

    return prompt_fn


def register_prompts(mcp: FastMCP) -> None:
    """Discover and register all markdown prompts in the prompts/ directory."""
    for md_file in sorted(_PROMPTS_DIR.glob("*.md")):
        description, body = load_prompt(md_file)
        prompt_name = md_file.stem
        mcp.prompt(name=prompt_name, description=description)(_make_prompt(body))
