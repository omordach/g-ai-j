from gaij.html_renderer import render_html


def test_render_full_fidelity_png_unit():
    html = "<p>Hi<img src='cid:img1'></p>"
    inline_parts = [
        {
            "filename": "img.png",
            "mime_type": "image/png",
            "data_bytes": b"img",
            "is_inline": True,
            "content_id": "img1",
        }
    ]
    png_bytes, name = render_html(html, inline_parts, "png")
    assert name.endswith(".png")
    assert png_bytes.startswith(b"PNGFAKE")
