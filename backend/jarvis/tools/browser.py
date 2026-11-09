"""Browser automation with Playwright (its own Chromium build, falling back to Edge) in a
dedicated JARVIS profile, separate from the user's normal browser profile.

All page content is returned as UNTRUSTED data. These tools only read; they never
submit forms, log in, pay, or bypass CAPTCHAs.
"""
from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import parse_qs, quote, quote_plus, unquote, urlparse

import httpx
from pydantic import BaseModel, Field

from jarvis.config import DATA_DIR
from jarvis.security.secrets import get_secret
from jarvis.tools.base import Assessment, Risk, Tool, ToolResult

log = logging.getLogger(__name__)
MAX_PAGE_CHARS = 6000
BLOCKED_SCHEMES = {"file", "javascript", "data", "chrome", "edge", "about"}

EXTRACT_JS = """
() => {
  const drop = ['script','style','noscript','nav','footer','header','aside','form','iframe','svg'];
  const root = (document.querySelector('article') || document.querySelector('main') || document.body).cloneNode(true);
  drop.forEach(t => root.querySelectorAll(t).forEach(e => e.remove()));
  const text = (root.innerText || '').replace(/\\n{3,}/g, '\\n\\n').trim();
  return { title: document.title, text };
}
"""


def _check_url(url: str) -> str:
    u = url.strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    if p.scheme.lower() not in ("http", "https") or p.scheme.lower() in BLOCKED_SCHEMES:
        raise ValueError("only http(s) URLs are allowed")
    host = (p.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local"):
        raise ValueError("local network addresses are not allowed for browsing")
    return u


class BrowserService:
    """Lazily started persistent Edge context, shared by browser tools."""

    def __init__(self, headless: bool = True, settings_getter=None):
        self.headless = headless
        self._settings = settings_getter
        self._pw = None
        self._ctx = None
        self._lock = asyncio.Lock()

    async def context(self):
        async with self._lock:
            if self._ctx is None:
                from playwright.async_api import async_playwright
                self._pw = await async_playwright().start()
                profile = DATA_DIR / "browser-profile"
                profile.mkdir(parents=True, exist_ok=True)
                headless = self.headless
                if self._settings is not None:
                    headless = not self._settings().web.browser_visible
                opts = dict(headless=headless, viewport={"width": 1280, "height": 860})
                try:  # Playwright's own Chromium build (separate from the user's browsers)
                    self._ctx = await self._pw.chromium.launch_persistent_context(str(profile), **opts)
                except Exception as e:
                    log.warning("Playwright Chromium unavailable (%s); trying installed Edge", e)
                    self._ctx = await self._pw.chromium.launch_persistent_context(str(profile), channel="msedge", **opts)
                self._ctx.set_default_timeout(25000)
            return self._ctx

    async def new_page(self):
        ctx = await self.context()
        pages = [p for p in ctx.pages if p.url == "about:blank"]
        return pages[0] if pages else await ctx.new_page()

    async def read(self, url: str) -> dict:
        page = await self.new_page()
        await page.goto(_check_url(url), wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        data = await page.evaluate(EXTRACT_JS)
        data["url"] = page.url
        return data

    async def search(self, query: str, limit: int = 6) -> list[dict]:
        """Brave Search API (if a key is saved), then Bing / DuckDuckGo pages, plus Wikipedia (if a contact is set).
        Results unrelated to the query are dropped. Bot checks are never bypassed."""
        results: list[dict] = []
        key = get_secret("brave_api_key")
        engines = ([self._search_brave_api] if key else []) + [self._search_bing, self._search_ddg]
        for engine in engines:
            try:
                results = _relevant(query, await engine(query, limit))
            except Exception as e:
                log.info("%s failed: %s", engine.__name__, e)
                results = []
            if results:
                break
        wiki = []
        contact = self._settings().web.wikipedia_contact if self._settings else ""
        try:
            if contact:
                wiki = await search_wikipedia(query, 3, contact)
        except Exception as e:
            log.info("wikipedia failed: %s", e)
        merged = results + [w for w in wiki if w["url"] not in {r["url"] for r in results}]
        if not merged:
            raise RuntimeError("No usable search results (engines returned nothing relevant or showed a bot check). "
                               "JARVIS does not bypass bot checks. Tip: add a free Brave Search API key or a Wikipedia contact in Settings → Web.")
        return merged[:limit]

    async def _search_brave_api(self, query: str, limit: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": limit},
                            headers={"Accept": "application/json", "X-Subscription-Token": get_secret("brave_api_key") or ""})
        r.raise_for_status()
        return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": re.sub(r"<[^>]+>", "", x.get("description", ""))}
                for x in r.json().get("web", {}).get("results", [])]

    async def _search_bing(self, query: str, limit: int) -> list[dict]:
        page = await self.new_page()
        await page.goto("https://www.bing.com/search?q=" + quote_plus(query), wait_until="domcontentloaded")
        rows = await page.evaluate("""
          () => [...document.querySelectorAll('li.b_algo')].map(r => ({
            title: r.querySelector('h2')?.innerText || '',
            url: r.querySelector('h2 a')?.href || '',
            snippet: r.querySelector('.b_caption p, .b_lineclamp2, .b_algoSlug')?.innerText || ''
          }))
        """)
        out = []
        for r in rows:
            url = _unwrap_bing(r.get("url", ""))
            if url.startswith("http") and "bing.com" not in urlparse(url).netloc:
                out.append({"title": r["title"].strip(), "url": url, "snippet": r["snippet"].strip()})
            if len(out) >= limit:
                break
        return out

    async def _search_ddg(self, query: str, limit: int) -> list[dict]:
        page = await self.new_page()
        await page.goto("https://html.duckduckgo.com/html/?q=" + quote_plus(query), wait_until="domcontentloaded")
        rows = await page.evaluate("""
          () => [...document.querySelectorAll('.result')].map(r => ({
            title: r.querySelector('.result__a')?.innerText || '',
            url: r.querySelector('.result__a')?.href || '',
            snippet: r.querySelector('.result__snippet')?.innerText || ''
          }))
        """)
        out = []
        for r in rows:
            url = r.get("url", "")
            if "duckduckgo.com/l/" in url:  # unwrap redirect links
                url = unquote(parse_qs(urlparse(url).query).get("uddg", [url])[0])
            if not url.startswith("http") or "duckduckgo.com/y.js" in url:
                continue  # skip ads
            out.append({"title": r["title"].strip(), "url": url, "snippet": r["snippet"].strip()})
            if len(out) >= limit:
                break
        return out

    async def tabs(self) -> list[dict]:
        if self._ctx is None:
            return []
        return [{"index": i, "url": p.url, "title": await p.title()} for i, p in enumerate(self._ctx.pages)]

    async def close_tab(self, index: int) -> bool:
        if self._ctx is None or index >= len(self._ctx.pages):
            return False
        await self._ctx.pages[index].close()
        return True

    async def shutdown(self):
        try:
            if self._ctx:
                await self._ctx.close()
            if self._pw:
                await self._pw.stop()
        finally:
            self._ctx = self._pw = None


_STOP = {"the", "and", "for", "with", "what", "how", "best", "der", "die", "das", "und", "mit", "wie", "ist",
         "عن", "في", "من", "على", "ما", "هو", "هي", "أفضل", "افضل", "شو", "كيف", "ابحث", "لي"}


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[\w؀-ۿ]+", text.lower()) if len(t) > 2 and t not in _STOP}


def _relevant(query: str, results: list[dict]) -> list[dict]:
    """Drop results that share no meaningful word with the query (protects against junk/decoy result pages)."""
    q = _terms(query)
    if not q:
        return results
    return [r for r in results if q & _terms(r.get("title", "") + " " + r.get("snippet", "") + " " + r.get("url", ""))]


def _query_lang(q: str) -> str:
    if re.search(r"[؀-ۿ]", q):
        return "ar"
    if re.search(r"[äöüß]|\b(und|der|die|das|wie|was|ist)\b", q, re.I):
        return "de"
    return "en"


async def search_wikipedia(query: str, limit: int = 3, contact: str = "") -> list[dict]:
    """Official MediaWiki search API - free, no key, allowed for automated use."""
    lang = _query_lang(query)
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": f"JARVIS-AI/0.1 ({contact}; personal desktop assistant) httpx/{httpx.__version__}"}) as c:
        r = await c.get(f"https://{lang}.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json", "utf8": 1})
    r.raise_for_status()
    hits = r.json().get("query", {}).get("search", [])
    return [{"title": f"Wikipedia: {h['title']}", "url": f"https://{lang}.wikipedia.org/wiki/{quote(h['title'].replace(' ', '_'))}",
             "snippet": re.sub(r"<[^>]+>", "", h.get("snippet", ""))} for h in hits]


def _unwrap_bing(url: str) -> str:
    """Bing wraps result links as /ck/a?...&u=a1<base64url(target)>."""
    if "bing.com/ck/a" not in url:
        return url
    import base64
    u = parse_qs(urlparse(url).query).get("u", [""])[0]
    if u.startswith("a1"):
        b = u[2:]
        try:
            return base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8", "replace")
        except Exception:
            return url
    return url


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + " …[truncated]"


class SearchArgs(BaseModel):
    query: str
    max_results: int = Field(6, ge=1, le=10)


class WebSearch(Tool):
    name = "web_search"
    description = "Search the web in JARVIS's automation browser and return titles, URLs and snippets."
    Args = SearchArgs
    risk = Risk.LOW

    def assess(self, args, ctx):
        return Assessment(Risk.LOW, True, f"Web search: {args.query}")

    async def run(self, args, ctx):
        res = await ctx.services.browser.search(args.query, args.max_results)
        if not res:
            return ToolResult(False, "No search results.")
        text = "\n\n".join(f"[{i+1}] {r['title']}\n{r['url']}\n{r['snippet']}" for i, r in enumerate(res))
        return ToolResult(True, text, {"results": res}, untrusted=True)


class BrowseArgs(BaseModel):
    url: str


class BrowsePage(Tool):
    name = "browse_page"
    description = "Open a web page in the automation browser and return its readable text (read-only)."
    Args = BrowseArgs
    risk = Risk.LOW

    def assess(self, args, ctx):
        return Assessment(Risk.LOW, True, f"Read web page {args.url}")

    async def run(self, args, ctx):
        d = await ctx.services.browser.read(args.url)
        return ToolResult(True, f"TITLE: {d['title']}\nURL: {d['url']}\n\n{_clip(d['text'], MAX_PAGE_CHARS)}",
                          {"url": d["url"], "title": d["title"], "chars": len(d["text"])}, untrusted=True)


class ResearchArgs(BaseModel):
    topic: str = Field(..., description="Topic or question to research")
    pages: int = Field(3, ge=1, le=5, description="How many result pages to read")


class ResearchTopic(Tool):
    name = "research_topic"
    description = ("Research a topic: web search, then read the top pages in the browser and return extracts with "
                   "sources so you can write a summary. Use this for 'research X' requests.")
    Args = ResearchArgs
    risk = Risk.LOW

    def assess(self, args, ctx):
        return Assessment(Risk.LOW, True, f"Research '{args.topic}' (search + read {args.pages} pages)")

    async def run(self, args, ctx):
        b = ctx.services.browser
        results = await b.search(args.topic, 8)
        sources, chunks = [], []
        per_page = max(1500, 7000 // args.pages)
        for r in results:
            if len(sources) >= args.pages:
                break
            if re.search(r"(authwall|/login|signin|sign-in|/account)", r["url"], re.I):
                continue  # never try to get past login walls
            try:
                d = await asyncio.wait_for(b.read(r["url"]), timeout=30)
            except Exception as e:
                log.info("skip %s: %s", r["url"], e)
                continue
            if len(d["text"]) < 300:
                continue
            sources.append({"title": d["title"] or r["title"], "url": d["url"]})
            chunks.append(f"SOURCE [{len(sources)}] {d['title']} — {d['url']}\n{_clip(d['text'], per_page)}")
        if not sources:
            return ToolResult(False, "Could not read any result pages.", {"results": results})
        return ToolResult(True, "\n\n---\n\n".join(chunks), {"sources": sources}, untrusted=True)


class NoArgs(BaseModel):
    pass


class ListTabs(Tool):
    name = "list_browser_tabs"
    description = "List the tabs open in JARVIS's automation browser."
    Args = NoArgs
    risk = Risk.LOW

    async def run(self, args, ctx):
        tabs = await ctx.services.browser.tabs()
        return ToolResult(True, "\n".join(f"{t['index']}: {t['title']} — {t['url']}" for t in tabs) or "No tabs open.",
                          {"tabs": tabs})


class CloseTabArgs(BaseModel):
    index: int = Field(..., ge=0)


class CloseTab(Tool):
    name = "close_browser_tab"
    description = "Close a tab in JARVIS's automation browser by index (see list_browser_tabs)."
    Args = CloseTabArgs
    risk = Risk.LOW

    async def run(self, args, ctx):
        ok = await ctx.services.browser.close_tab(args.index)
        return ToolResult(ok, "Tab closed." if ok else "No such tab.")


TOOLS = [WebSearch(), BrowsePage(), ResearchTopic(), ListTabs(), CloseTab()]
