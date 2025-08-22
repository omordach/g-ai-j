import re
from typing import Any, Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

PLACEHOLDER_RE = re.compile(r"__INLINE_IMAGE__\[([^\]]+)\]__")


def _text_node(text: str, marks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def _replace_placeholders(text: str, inline_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        cid = match.group(1)
        name = inline_map.get(cid, cid)
        return f"[inline image: {name}]"

    return PLACEHOLDER_RE.sub(repl, text)


def _convert_inline(node: Any, inline_map: dict[str, str], marks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if marks is None:
        marks = []
    result: list[dict[str, Any]] = []
    if isinstance(node, NavigableString):
        text = _replace_placeholders(str(node), inline_map)
        if text.strip():
            result.append(_text_node(text, marks or None))
        return result
    if isinstance(node, Tag):
        name = node.name.lower()
        new_marks = marks.copy()
        if name in {"strong", "b"}:
            new_marks.append({"type": "strong"})
        elif name in {"em", "i"}:
            new_marks.append({"type": "em"})
        elif name == "u":
            new_marks.append({"type": "underline"})
        elif name == "a":
            new_marks.append({"type": "link", "attrs": {"href": node.get("href", "")}})
        for child in node.children:
            result.extend(_convert_inline(child, inline_map, new_marks))
    return result


def _convert_element(elem: Any, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    if isinstance(elem, NavigableString):
        text = _replace_placeholders(str(elem), inline_map).strip()
        if text:
            return [{"type": "paragraph", "content": [_text_node(text)]}]
        return []
    if not isinstance(elem, Tag):
        return []

    name = elem.name.lower()
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        return [
            {
                "type": "heading",
                "attrs": {"level": level},
                "content": _convert_inline(elem, inline_map),
            }
        ]
    if name == "p":
        return [{"type": "paragraph", "content": _convert_inline(elem, inline_map)}]
    if name in {"ul", "ol"}:
        list_type = "bulletList" if name == "ul" else "orderedList"
        items = []
        for li in elem.find_all("li", recursive=False):
            items.append({"type": "listItem", "content": _convert_element(li, inline_map)})
        return [{"type": list_type, "content": items}]
    if name == "li":
        return [{"type": "paragraph", "content": _convert_inline(elem, inline_map)}]
    if name == "img":
        src = elem.get("src", "")
        m = PLACEHOLDER_RE.search(src)
        if m:
            cid = m.group(1)
            filename = inline_map.get(cid, cid)
            return [{"type": "paragraph", "content": [_text_node(f"[inline image: {filename}]")]}]
        return []
    if name == "blockquote":
        inner: list[dict[str, Any]] = []
        for child in elem.children:
            inner.extend(_convert_element(child, inline_map))
        return [{"type": "blockquote", "content": inner}]
    # Fallback: treat as paragraph
    return [{"type": "paragraph", "content": _convert_inline(elem, inline_map)}]


def build_adf_from_html(html: str, inline_map: dict[str, str] | None = None) -> dict[str, Any]:
    inline_map = inline_map or {}
    soup = BeautifulSoup(html or "", "html.parser")
    body: Iterable[Any]
    if soup.body:
        body = soup.body.contents
    else:
        body = soup.contents
    content: list[dict[str, Any]] = []
    for elem in body:
        content.extend(_convert_element(elem, inline_map))
    if not content:
        content = [{"type": "paragraph"}]
    return {"type": "doc", "version": 1, "content": content}


def prepend_note(adf: dict[str, Any], note: str) -> dict[str, Any]:
    content = [
        {"type": "paragraph", "content": [{"type": "text", "text": note}]}
    ] + list(adf.get("content", []))
    return {"type": "doc", "version": 1, "content": content}
