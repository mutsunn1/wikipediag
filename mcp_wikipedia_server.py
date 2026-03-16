"""
MCP Server for Wikipedia Tools
支持自动分类工作流的Wikipedia工具

运行方式:
    python mcp_wikipedia_server.py
    
或使用 uv:
    uv run mcp_wikipedia_server.py
"""

import asyncio
import json
from typing import Any, Dict, List
from urllib.parse import quote

import aiohttp
from mcp.server import Server
from mcp.types import TextContent, Tool

app = Server("wikipedia-auto-categorization-server")


class WikipediaClient:
    """Wikipedia API客户端"""
    
    BASE_URL = "https://en.wikipedia.org"
    API_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "OxygentWikiCrawler/1.0"}
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索Wikipedia页面"""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1
        }
        
        async with self.session.get(self.API_URL, params=params) as resp:
            data = await resp.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                results.append({
                    "title": item["title"],
                    "pageid": item["pageid"],
                    "snippet": item.get("snippet", ""),
                    "url": f"{self.BASE_URL}/wiki/{quote(item['title'].replace(' ', '_'))}"
                })
            return results
    
    async def get_content(self, title: str) -> Dict:
        """获取页面内容（用于自动分类分析）"""
        params = {
            "action": "query",
            "prop": "extracts|info",
            "titles": title,
            "explaintext": 1,
            "exlimit": 1,
            "exchars": 8000,  # 获取更多内容用于分析
            "format": "json",
            "utf8": 1
        }
        
        async with self.session.get(self.API_URL, params=params) as resp:
            data = await resp.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_data in pages.items():
                if "missing" in page_data:
                    return {"error": "Page not found"}
                
                content = page_data.get("extract", "")
                return {
                    "title": page_data.get("title", title),
                    "pageid": page_id,
                    "content": content,
                    "content_preview": content[:3000] if len(content) > 3000 else content,
                    "url": f"{self.BASE_URL}/wiki/{quote(title.replace(' ', '_'))}",
                    "word_count": len(content.split()),
                    "char_count": len(content)
                }
            return {"error": "No content found"}


@app.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="wikipedia_search",
            description="Search Wikipedia pages by keyword for auto-categorization workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="wikipedia_get_page",
            description="Get Wikipedia page content with full text for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Page title"}
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="wikipedia_crawl_domain",
            description="Crawl multiple Wikipedia pages for a domain (auto-categorization workflow). Fetches diverse pages covering different subtopics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name (e.g., 'Computer Science')"},
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of search queries covering different subtopics"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Max total pages to crawl",
                        "default": 50
                    }
                },
                "required": ["domain", "queries"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """调用工具"""
    
    async with WikipediaClient() as client:
        if name == "wikipedia_search":
            results = await client.search(
                arguments["query"],
                arguments.get("limit", 10)
            )
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        
        elif name == "wikipedia_get_page":
            content = await client.get_content(arguments["title"])
            return [TextContent(type="text", text=json.dumps(content, indent=2))]
        
        elif name == "wikipedia_crawl_domain":
            """为指定领域爬取多个页面"""
            all_pages = []
            seen_titles = set()
            pages_collected = 0
            max_pages = arguments.get("max_pages", 50)
            queries = arguments["queries"]
            
            for query in queries:
                if pages_collected >= max_pages:
                    break
                
                remaining = max_pages - pages_collected
                limit = min(5, remaining)  # 每个查询最多5个
                
                search_results = await client.search(query, limit)
                
                for result in search_results:
                    if pages_collected >= max_pages:
                        break
                    
                    title = result["title"]
                    if title in seen_titles:
                        continue
                    
                    page_content = await client.get_content(title)
                    if "error" not in page_content:
                        all_pages.append(page_content)
                        seen_titles.add(title)
                        pages_collected += 1
                    
                    await asyncio.sleep(0.3)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "domain": arguments["domain"],
                    "total_crawled": len(all_pages),
                    "unique_pages": len(seen_titles),
                    "pages": all_pages
                }, indent=2)
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """启动MCP Server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
