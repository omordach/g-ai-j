import re
from collections.abc import Callable, Iterable
from typing import Any

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

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


MARK_TAGS: dict[str, dict[str, Any]] = {
    "strong": {"type": "strong"},
    "b": {"type": "strong"},
    "em": {"type": "em"},
    "i": {"type": "em"},
    "u": {"type": "underline"},
}


def _convert_inline(
    node: Any, inline_map: dict[str, str], marks: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    if marks is None:
        marks = []
    if isinstance(node, NavigableString):
        text = _replace_placeholders(str(node), inline_map)
        return [_text_node(text, marks or None)] if text.strip() else []

    if isinstance(node, Tag):
        name = node.name.lower()
        new_marks = marks + ([MARK_TAGS[name]] if name in MARK_TAGS else [])
        if name == "a":
            href_attr = node.get("href")
            href = href_attr if isinstance(href_attr, str) else ""
            new_marks.append({"type": "link", "attrs": {"href": href}})
        result: list[dict[str, Any]] = []
        for child in node.children:
            result.extend(_convert_inline(child, inline_map, new_marks))
        return result

    return []


def _handle_heading(elem: Tag, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    level = int(elem.name[1])
    return [
        {
            "type": "heading",
            "attrs": {"level": level},
            "content": _convert_inline(elem, inline_map),
        }
    ]


def _handle_paragraph(elem: Tag, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    return [{"type": "paragraph", "content": _convert_inline(elem, inline_map)}]


def _handle_list(elem: Tag, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    list_type = "bulletList" if elem.name == "ul" else "orderedList"
    items = [
        {"type": "listItem", "content": _convert_element(li, inline_map)}
        for li in elem.find_all("li", recursive=False)
    ]
    return [{"type": list_type, "content": items}]


def _handle_img(elem: Tag, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    src_attr = elem.get("src")
    src = src_attr if isinstance(src_attr, str) else ""
    m = PLACEHOLDER_RE.search(src)
    if m:
        cid = m.group(1)
        filename = inline_map.get(cid, cid)
        return [
            {
                "type": "paragraph",
                "content": [_text_node(f"[inline image: {filename}]")],
            }
        ]
    return []


def _handle_blockquote(elem: Tag, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    inner: list[dict[str, Any]] = []
    for child in elem.children:
        inner.extend(_convert_element(child, inline_map))
    return [{"type": "blockquote", "content": inner}]


HANDLERS: dict[str, Callable[[Tag, dict[str, str]], list[dict[str, Any]]]] = {
    "p": _handle_paragraph,
    "ul": _handle_list,
    "ol": _handle_list,
    "img": _handle_img,
    "blockquote": _handle_blockquote,
    "h1": _handle_heading,
    "h2": _handle_heading,
    "h3": _handle_heading,
    "h4": _handle_heading,
    "h5": _handle_heading,
    "h6": _handle_heading,
}


def _convert_element(elem: Any, inline_map: dict[str, str]) -> list[dict[str, Any]]:
    if isinstance(elem, NavigableString):
        text = _replace_placeholders(str(elem), inline_map).strip()
        return [{"type": "paragraph", "content": [_text_node(text)]}] if text else []

    if not isinstance(elem, Tag):
        return []

    handler = HANDLERS.get(elem.name.lower())
    if handler:
        return handler(elem, inline_map)
    return _handle_paragraph(elem, inline_map)


def build_adf_from_html(html: str, inline_map: dict[str, str] | None = None) -> dict[str, Any]:
    inline_map = inline_map or {}
    soup = BeautifulSoup(html or "", "html.parser")
    body: Iterable[Any] = soup.body.contents if soup.body else soup.contents
    content: list[dict[str, Any]] = []
    for elem in body:
        content.extend(_convert_element(elem, inline_map))
    if not content:
        content = [{"type": "paragraph"}]
    return {"type": "doc", "version": 1, "content": content}


def prepend_note(adf: dict[str, Any], note: str) -> dict[str, Any]:
    content = [
        {"type": "paragraph", "content": [{"type": "text", "text": note}]},
        *adf.get("content", []),
    ]
    return {"type": "doc", "version": 1, "content": content}
