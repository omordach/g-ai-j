import base64
from typing import Any, List, Tuple


def render_html(html: str, inline_parts: List[dict[str, Any]], fmt: str = "pdf") -> Tuple[bytes, str]:
    """Render HTML to PDF/PNG bytes embedding inline images.

    This is a lightweight stand-in for real rendering libraries. It simply
    replaces ``cid:`` references with data URIs and returns the resulting HTML
    encoded as bytes with a fake PDF/PNG header so tests can assert output
    exists without heavy dependencies.
    """

    for part in inline_parts:
        cid = part.get("content_id")
        data = base64.b64encode(part.get("data_bytes", b""))
        mime = part.get("mime_type", "application/octet-stream")
        if cid:
            html = html.replace(f"cid:{cid}", f"data:{mime};base64,{data.decode()}")
    if fmt == "png":
        filename = "email-render.png"
        return b"PNGFAKE" + html.encode("utf-8"), filename
    filename = "email-render.pdf"
    return b"%PDF-FAKE\n" + html.encode("utf-8"), filename
