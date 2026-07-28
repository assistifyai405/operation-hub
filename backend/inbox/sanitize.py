"""HTML sanitization for inbound email bodies (stdlib only)."""
from __future__ import annotations

import html as html_lib
import re
from html.parser import HTMLParser
from typing import List, Tuple

ALLOWED_TAGS = {
    "a", "b", "strong", "i", "em", "u", "p", "br", "ul", "ol", "li",
    "blockquote", "pre", "code", "span", "div", "table", "thead", "tbody",
    "tr", "th", "td", "h1", "h2", "h3", "h4",
}
ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}
# Void / always-drop tags must not bump the skip counter (no end tag in HTML).
DROP_VOID = {"img", "link", "meta", "br", "hr", "source", "track", "wbr", "input"}
DROP_BLOCK = {"script", "style", "iframe", "object", "embed", "svg", "noscript"}
SAFE_URI = re.compile(r"^(https?://|mailto:|#)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._out: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_VOID:
            return
        if tag in DROP_BLOCK:
            self._skip += 1
            return
        if self._skip or tag not in ALLOWED_TAGS:
            return
        allowed = ALLOWED_ATTRS.get(tag, set())
        cleaned = []
        for k, v in attrs:
            k = k.lower()
            if k not in allowed or v is None:
                continue
            if k == "href":
                val = v.strip()
                if not SAFE_URI.match(val) or "javascript:" in val.lower():
                    continue
                cleaned.append(f'href="{html_lib.escape(val, quote=True)}" rel="noopener noreferrer"')
            else:
                cleaned.append(f'{k}="{html_lib.escape(v, quote=True)}"')
        attr_s = (" " + " ".join(cleaned)) if cleaned else ""
        if tag == "br":
            self._out.append("<br/>")
        else:
            self._out.append(f"<{tag}{attr_s}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_VOID:
            return
        if tag in DROP_BLOCK:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or tag not in ALLOWED_TAGS or tag == "br":
            return
        self._out.append(f"</{tag}>")
    def handle_data(self, data):
        if self._skip:
            return
        self._out.append(html_lib.escape(data))

    def handle_entityref(self, name):
        if not self._skip:
            self._out.append(f"&{name};")

    def handle_charref(self, name):
        if not self._skip:
            self._out.append(f"&#{name};")

    def result(self) -> str:
        return "".join(self._out)


def sanitize_html(raw: str | None) -> str:
    if not raw:
        return ""
    parser = _Sanitizer()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return html_lib.escape(re.sub(r"<[^>]+>", "", raw))
    return parser.result()


def html_to_text(raw: str | None) -> str:
    if not raw:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    t = re.sub(r"</p\s*>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html_lib.unescape(t).strip()


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def parse_address_list(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(normalize_email(item.get("email") or item.get("address") or ""))
            else:
                out.append(normalize_email(str(item)))
        return [e for e in out if e and "@" in e]
    # "Name <a@b.com>, c@d.com"
    parts = re.split(r"\s*,\s*", str(value))
    out = []
    for p in parts:
        m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", p)
        if m:
            out.append(normalize_email(m.group(0)))
    return out
