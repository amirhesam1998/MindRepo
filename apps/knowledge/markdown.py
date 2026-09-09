"""One safe Markdown rendering path for private knowledge content."""

import nh3
from markdown_it import MarkdownIt


_markdown = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table").enable("strikethrough")
_tags = {"p", "br", "h1", "h2", "h3", "h4", "strong", "em", "s", "ul", "ol", "li", "blockquote", "code", "pre", "a", "hr", "table", "thead", "tbody", "tr", "th", "td"}
_attributes = {"a": {"href", "title", "target"}, "code": {"class"}}


def render_markdown(source: str) -> str:
    """Render Markdown with raw HTML disabled and a tight allowlist."""
    html = _markdown.render(source or "")
    return nh3.clean(html, tags=_tags, attributes=_attributes, url_schemes={"http", "https", "mailto"}, link_rel="noopener noreferrer")
