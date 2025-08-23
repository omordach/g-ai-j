from gaij.html_renderer import render_html


def test_render_html_preserves_linebreaks_in_pdf():
    html = "<p>Line1<br>Line2</p>"
    pdf_bytes, name = render_html(html, [], fmt="pdf")
    assert name.endswith(".pdf")
    # The PDF stream should render each line separately, moving the cursor
    # down between them.  ``Td`` operations indicate line breaks.
    assert b"(Line1) Tj 0 -14 Td" in pdf_bytes
    assert b"0 -14 Td (Line2) Tj" in pdf_bytes
