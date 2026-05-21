import os
import asyncio
import aiohttp
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional


class WebSearchScraper:
    BLOCKED_SOURCE_DOMAINS = {
        "facebook.com",
        "fb.com",
        "instagram.com",
        "linkedin.com",
        "m.facebook.com",
        "music.youtube.com",
        "pinterest.com",
        "t.co",
        "threads.net",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "youtu.be",
    }

    def __init__(self):
        # Fallback to empty string, but warn if missing
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not self.tavily_api_key:
            print("WARNING: TAVILY_API_KEY is not set in environment variables.")

    def is_blocked_source_url(self, url: str) -> bool:
        """Skip social/video platforms that usually provide poor scrapeable research text."""
        hostname = urlparse(url).hostname or ""
        normalized_hostname = hostname.lower().removeprefix("www.")
        return any(
            normalized_hostname == blocked_domain
            or normalized_hostname.endswith(f".{blocked_domain}")
            for blocked_domain in self.BLOCKED_SOURCE_DOMAINS
        )

    async def search_tavily(self, session: aiohttp.ClientSession, query: str, max_results: int = 3) -> List[Dict]:
        """Executes a single search query against Tavily."""
        if not self.tavily_api_key:
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_raw_content": False
        }
        try:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                print(f"Tavily search failed for '{query}' with status {response.status}.")
        except Exception as e:
            print(f"Search failed for query '{query}': {e}")
        return []

    def build_unreachable_page(
        self,
        url: str,
        title: str,
        reason: str,
        status: int | None = None,
    ) -> Dict[str, Any]:
        """Return a placeholder page when a relevant result cannot be fetched."""
        status_note = f" HTTP status: {status}." if status is not None else ""
        return {
            "url": url,
            "title": title or "Unknown Title",
            "content": f"[Content unreachable] The page could not be read. Reason: {reason}.{status_note}",
            "domain": url.split("//")[-1].split("/")[0],
            "retrieved_at": datetime.now().isoformat(),
            "content_unreachable": True,
            "fetch_error": reason,
            "http_status": status,
        }

    async def fetch_and_clean_page(self, session: aiohttp.ClientSession, url: str, title: str) -> Optional[Dict[str, Any]]:
        """Downloads HTML and strips out boilerplate to save tokens."""
        try:
            # 10 second timeout, ignore SSL verification errors common on random blogs
            async with session.get(url, timeout=10, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Destroy layout tags that contain no useful research data
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button']):
                        tag.decompose()
                        
                    # Extract pure text, collapsing multiple spaces
                    text = ' '.join(soup.stripped_strings)
                    
                    # Cap at 8000 characters per page to prevent massive memory/token flooding
                    return {
                        "url": url,
                        "title": title,
                        "content": text[:8000],
                        "domain": url.split("//")[-1].split("/")[0], # Extract domain for citations
                        "retrieved_at": datetime.now().isoformat()
                    }
                return self.build_unreachable_page(
                    url,
                    title,
                    reason="non-200 response",
                    status=response.status,
                )
        except asyncio.TimeoutError:
            return self.build_unreachable_page(url, title, reason="request timed out")
        except aiohttp.ClientError as error:
            return self.build_unreachable_page(url, title, reason=type(error).__name__)
        except Exception as error:
            return self.build_unreachable_page(url, title, reason=type(error).__name__)

    def select_top_unique_results(
        self,
        queries: List[str],
        search_results_groups: List[List[Dict]],
        top_per_query: int = 1,
    ) -> List[Dict[str, Any]]:
        """Choose the highest-ranked non-duplicate result for each query."""
        seen_urls = set()
        selected_results = []

        for query, results in zip(queries, search_results_groups):
            selected_for_query = 0
            for rank, item in enumerate(results, start=1):
                url = item.get("url")
                if not url or url in seen_urls or self.is_blocked_source_url(url):
                    continue

                seen_urls.add(url)
                selected_results.append({
                    "url": url,
                    "title": item.get("title", "Unknown Title"),
                    "snippet": item.get("content") or item.get("snippet") or "",
                    "score": item.get("score"),
                    "query": query,
                    "rank": rank,
                })
                selected_for_query += 1

                if selected_for_query >= top_per_query:
                    break

        return selected_results

    async def execute_concurrent_research(
        self,
        queries: List[str],
        max_results: int = 5,
        top_per_query: int = 1,
    ) -> List[Dict[str, Any]]:
        """Main entry point: fetches the top unique cleaned page for each query."""
        async with aiohttp.ClientSession() as session:
            # 1. Fire all search queries at the same time
            search_tasks = [self.search_tavily(session, q, max_results=max_results) for q in queries]
            search_results_groups = await asyncio.gather(*search_tasks)
            
            # 2. Pick the best available non-duplicate result for each query
            selected_results = self.select_top_unique_results(
                queries,
                search_results_groups,
                top_per_query=top_per_query,
            )

            # 3. Fire all page scraping tasks simultaneously
            fetch_tasks = [
                self.fetch_and_clean_page(session, result["url"], result["title"])
                for result in selected_results
            ]
            scraped_pages = await asyncio.gather(*fetch_tasks)
            
            # Keep unreachable placeholders so the answerer knows evidence was missing.
            valid_pages = []
            for result, page in zip(selected_results, scraped_pages):
                if page is not None and (page.get("content_unreachable") or len(page.get("content", "")) > 50):
                    page["query"] = result["query"]
                    page["rank"] = result["rank"]
                    page["snippet"] = result.get("snippet", "")
                    page["score"] = result.get("score")
                    valid_pages.append(page)
            
            return valid_pages
