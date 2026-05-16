"""Web search tool using DuckDuckGo HTML (no API key needed)."""

import urllib.request
import urllib.parse
import re
from deepseek_code.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    name = "WebSearch"
    description = "Search the web. Returns titles, snippets, URLs."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
                "minLength": 2,
            },
        },
        "required": ["query"],
    }

    def execute(self, params: dict) -> ToolResult:
        query = params.get("query", "")
        if not query.strip():
            return ToolResult(content="Empty search query", is_error=True)

        try:
            results = self._search(query)
        except Exception:
            return ToolResult(
                content=f"Search failed. Try using WebFetch with a known URL. Query: {query}",
                is_error=True,
            )

        if not results:
            return ToolResult(content=f"No results found for: {query}")

        lines = []
        for i, r in enumerate(results[:8], 1):
            title = r.get("title", "Untitled")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            lines.append(f"{i}. {title}\n   {snippet}\n   {url}")

        return ToolResult(content="\n\n".join(lines))

    def _search(self, query: str) -> list[dict]:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 DeepSeekCode/0.1"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = []
        # Extract result blocks: title link + snippet
        for m in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            r'.*?<a[^>]*class="result__snippet"[^>]*>([^<]+)</a>',
            html, re.DOTALL,
        ):
            results.append({
                "title": m.group(2).strip(),
                "url": m.group(1).strip(),
                "snippet": m.group(3).strip(),
            })

        if not results:
            # Fallback: looser match
            for m in re.finditer(
                r'class="result__title"[^>]*>.*?href="([^"]+)"[^>]*>([^<]+)<',
                html,
            ):
                results.append({
                    "title": m.group(2).strip(),
                    "url": m.group(1).strip(),
                    "snippet": "",
                })

        return results
