import base64

from gaij.html_to_adf import build_adf_from_html


def test_inline_images_cid_mapping(app_setup):
    gmail_client = app_setup["gmail_client"]
    message_json = {
        "id": "1",
        "payload": {
            "mimeType": "multipart/related",
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.urlsafe_b64encode(
                            b"<html><body><img src='cid:abc123'></body></html>"
                        ).decode()
                    },
                },
                {
                    "filename": "photo.png",
                    "mimeType": "image/png",
                    "body": {"data": base64.urlsafe_b64encode(b"img").decode()},
                    "headers": [{"name": "Content-ID", "value": "<abc123>"}],
                },
            ],
        },
    }
    html, inline_parts = gmail_client.extract_html_and_inline_parts(message_json)
    assert "__INLINE_IMAGE__[abc123]__" in html
    inline_map = {p["content_id"]: p["filename"] for p in inline_parts}
    adf = build_adf_from_html(html, inline_map)
    text_nodes = [n.get("text") for p in adf["content"] for n in p.get("content", [])]
    assert any(t and t.startswith("[inline image: photo.png]") for t in text_nodes)


def test_inline_images_render_with_ids():
    html = "<html><body><img src='__INLINE_IMAGE__[abc]__'></body></html>"
    adf = build_adf_from_html(html, {"abc": "123"})
    media_nodes = [n for n in adf["content"] if n.get("type") == "mediaSingle"]
    assert media_nodes[0]["content"][0]["attrs"]["id"] == "123"
