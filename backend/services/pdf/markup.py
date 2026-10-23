import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL)

def escape_text(value: str | None) -> str:
    return html.escape(value or "", quote=False).replace("\n", "<br/>")

def to_markup(value: str | None) -> str:
    escaped = html.escape(value or "", quote=False)
    lines = []
    for line in escaped.split("\n"):
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if stripped.startswith("- ") or stripped.startswith("* "):
            lines.append(f"{indent}• {_inline(stripped[2:])}")
        else:
            lines.append(_inline(line))
    return "<br/>".join(lines)

def _inline(text: str) -> str:
    text = _BOLD.sub(r"<b>\1</b>", text)
    return _ITALIC.sub(r"<i>\1</i>", text)
