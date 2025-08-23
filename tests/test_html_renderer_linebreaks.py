from gaij.html_renderer import render_html


def test_render_html_preserves_linebreaks_in_pdf():
    html = "<p>Line1<br>Line2</p>"
    pdf_bytes, name = render_html(html, [], fmt="pdf")
    assert name.endswith(".pdf")
    assert b"Line1" in pdf_bytes and b"Line2" in pdf_bytes
