from gaij.html_to_adf import build_adf_from_html


def test_html_to_adf_handles_span_styles_and_line_breaks():
    html = (
        "<p>Line1<br>Line2"
        "<span style='font-weight:bold'>B</span>"
        "<span style='font-style:italic'>I</span>"
        "<span style='text-decoration:underline'>U</span>"
        "</p>"
    )
    adf = build_adf_from_html(html, {})
    para = adf["content"][0]
    nodes = para["content"]
    assert nodes[1]["type"] == "hardBreak"
    assert nodes[2]["text"] == "Line2"
    assert any(m["type"] == "strong" for m in nodes[3].get("marks", []))
    assert any(m["type"] == "em" for m in nodes[4].get("marks", []))
    assert any(m["type"] == "underline" for m in nodes[5].get("marks", []))
