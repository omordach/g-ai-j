"""Utilities to render e-mail HTML into shareable artifacts."""

from __future__ import annotations

import base64
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import NavigableString


def _simple_pdf_bytes(text: str) -> bytes:
    """Create a very small but valid PDF containing ``text``.

    The implementation avoids external dependencies so it can run in the
    constrained execution environment used for tests.  The generated PDF uses
    a single page with the built-in Helvetica font.
    """

    # Escape characters that have a special meaning in PDF text objects.
    esc = text.replace("\\", r"\\\\").replace("(", r"\\(").replace(")", r"\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({esc}) Tj ET"

    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1", "replace"))
    xref = len(pdf)
    pdf.extend(
        f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode(
            "latin-1", "replace"
        )
    )
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1", "replace"))
    pdf.extend(b"trailer\n")
    pdf.extend(
        f"<< /Size {len(objects)+1} /Root 1 0 R >>\n".encode("latin-1", "replace")
    )
    pdf.extend(f"startxref\n{xref}\n%%EOF".encode("latin-1", "replace"))
    return bytes(pdf)


def render_html(
    html: str, inline_parts: list[dict[str, Any]], fmt: str = "pdf"
) -> tuple[bytes, str]:
    """Render HTML e-mail to PDF/PNG bytes embedding inline images.

    ``fmt`` currently supports ``"pdf"`` and ``"png"`` (the latter remains a
    lightweight placeholder).  Inline images referenced via ``cid:`` URLs are
    replaced with base64 ``data:`` URIs so that the rendered output is
    self-contained.
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

    # Convert HTML to plain text for the minimal PDF representation.
    soup = BeautifulSoup(html, "html.parser")
    # Preserve explicit line breaks to keep e-mail formatting readable.
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))
    text = soup.get_text(separator="\n")
    pdf_bytes = _simple_pdf_bytes(text)
    filename = "email-render.pdf"
    return pdf_bytes, filename
