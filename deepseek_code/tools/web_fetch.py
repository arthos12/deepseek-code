"""Web fetch tool — HTTP GET, HTML-to-text conversion."""

import urllib.request
import urllib.error
from html.parser import HTMLParser

from deepseek_code.tools.base import BaseTool, ToolResult


class _TextExtractor(HTMLParser):
    """Extract visible text, properly skipping script/style/noscript/iframe/svg.
    Uses a depth counter so nested tags inside skip blocks are also suppressed."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_tags = {"script", "style", "noscript", "iframe", "svg"}
        self._skip_depth = 0
        self._block_tags = {"br", "p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self._skip_depth += 1
        elif tag.lower() in self._block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag.lower() in self._block_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)

    def get_text(self) -> str:
        raw = " ".join(self.parts)
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        return "\n".join(lines)


class WebFetchTool(BaseTool):
    name = "WebFetch"
    description = "Fetch a URL. Extracts readable text from HTML."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "prompt": {
                "type": "string",
                "description": "What information to extract from the page (for logging only)",
            },
        },
        "required": ["url"],
    }

    def execute(self, params: dict) -> ToolResult:
        url = params.get("url", "")
        if not url.startswith(("http://", "https://")):
            return ToolResult(content=f"Invalid URL: {url}", is_error=True)

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 DeepSeekCode/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()

            # Decode
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            try:
                text = raw.decode(charset, errors="replace")
            except Exception:
                text = raw.decode("latin-1", errors="replace")

            if "text/html" in content_type or text.strip().startswith("<"):
                parser = _TextExtractor()
                parser.feed(text)
                result = parser.get_text()
            else:
                result = text

            if len(result) > 10000:
                result = result[:10000] + "\n\n[Truncated at 10000 chars]"

            return ToolResult(content=result if result.strip() else "(Page appears empty)")

        except urllib.error.HTTPError as e:
            return ToolResult(content=f"HTTP {e.code}: {e.reason}", is_error=True)
        except urllib.error.URLError as e:
            return ToolResult(content=f"Connection error: {e.reason}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Fetch error: {e}", is_error=True)
