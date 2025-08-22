from gaij.html_to_adf import build_adf_from_html


def test_html_to_adf_basic():
    html = (
        "<h1>Title</h1>"
        "<p>This is <strong>bold</strong> and <em>italic</em> <u>under</u> "
        "<a href='https://example.com'>link</a></p>"
        "<ul><li>Item1</li><li>Item2</li></ul>"
        "<blockquote><p>Quote</p></blockquote>"
    )
    adf = build_adf_from_html(html, {})
    assert adf["content"][0]["type"] == "heading"
    para = adf["content"][1]
    texts = [n.get("text") for n in para["content"] if n.get("type") == "text"]
    assert "This is " in texts[0]
    marks = para["content"][1].get("marks")
    assert {m["type"] for m in marks} == {"strong"}
    lst = adf["content"][2]
    assert lst["type"] == "bulletList"
    assert lst["content"][0]["type"] == "listItem"
    block = adf["content"][3]
    assert block["type"] == "blockquote"
