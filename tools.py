"""
包含Wikipedia爬取、本地保存和Markdown生成功能
"""

import asyncio
import json
import os
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlparse

import aiohttp
from pydantic import Field

from oxygent.oxy import FunctionHub
from config import get_config, CrawlerConfig

# 注册工具包
wikipedia_tools = FunctionHub(name="wikipedia_tools")
file_tools = FunctionHub(name="file_tools")


# ============================================
# Wikipedia 爬取工具
# ============================================

class WikipediaCrawler:
    """Wikipedia页面爬取器"""
    
    BASE_URL = "https://en.wikipedia.org"
    SEARCH_API = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 3
        self.base_delay = 0.5
        self.proxy: Optional[str] = self._resolve_proxy()

    @staticmethod
    def _resolve_proxy() -> Optional[str]:
        """从配置和环境变量解析可选代理地址。"""
        config_proxy = (get_config().https_proxy or "").strip()
        env_proxy = (
            os.getenv("HTTPS_PROXY")
            or os.getenv("https_proxy")
            or ""
        ).strip()

        proxy = config_proxy or env_proxy
        if not proxy:
            return None

        # aiohttp 代理需要带协议头。
        if proxy.startswith("http://") or proxy.startswith("https://"):
            return proxy
        return f"http://{proxy}"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=25, connect=10),
            headers={
                "User-Agent": "OxygentWikiCrawler/1.0 (Educational Purpose)"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_pages(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索Wikipedia页面"""
        if not self.session:
            raise RuntimeError("Crawler not initialized. Use 'async with' context.")
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    self.SEARCH_API,
                    params=params,
                    proxy=self.proxy,
                ) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}")

                    data = await resp.json(content_type=None)
                    results = []
                    for item in data.get("query", {}).get("search", []):
                        results.append({
                            "title": item["title"],
                            "pageid": str(item["pageid"]),
                            "snippet": item.get("snippet", ""),
                            "url": f"{self.BASE_URL}/wiki/{quote(item['title'].replace(' ', '_'))}"
                        })
                    return results
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return [{"error": f"search failed: {str(e)}"}]
                backoff = self.base_delay * (2 ** attempt) + random.uniform(0, 0.2)
                await asyncio.sleep(backoff)
    
    async def get_page_content(self, title: str) -> Dict[str, Any]:
        """获取页面完整内容"""
        if not self.session:
            raise RuntimeError("Crawler not initialized. Use 'async with' context.")
        
        params = {
            "action": "query",
            "prop": "extracts|info",
            "titles": title,
            "explaintext": 1,
            "exlimit": 1,
            "exchars": 8000,
            "format": "json",
            "utf8": 1
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(
                    self.SEARCH_API,
                    params=params,
                    proxy=self.proxy,
                ) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}")

                    data = await resp.json(content_type=None)
                    pages = data.get("query", {}).get("pages", {})

                    for page_id, page_data in pages.items():
                        if "missing" in page_data:
                            return {"error": "Page not found"}

                        content = page_data.get("extract", "")
                        page_title = page_data.get("title", title)
                        return {
                            "title": page_title,
                            "pageid": page_id,
                            "content": content,
                            "url": f"{self.BASE_URL}/wiki/{quote(page_title.replace(' ', '_'))}",
                            "word_count": len(content.split()),
                            "char_count": len(content)
                        }

                    return {"error": "No content found"}
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return {"error": f"get_page_content failed: {str(e)}"}
                backoff = self.base_delay * (2 ** attempt) + random.uniform(0, 0.2)
                await asyncio.sleep(backoff)


# ============================================
# 工具函数注册
# ============================================

@wikipedia_tools.tool(
    description="Search Wikipedia pages by query keyword. Returns a list of page titles and URLs."
)
async def search_wikipedia(
    query: str = Field(description="Search query keyword"),
    limit: int = Field(description="Maximum number of results to return", default=10)
) -> str:
    """搜索Wikipedia页面"""
    async with WikipediaCrawler() as crawler:
        results = await crawler.search_pages(query, limit)
    return json.dumps(results, ensure_ascii=False, indent=2)


@wikipedia_tools.tool(
    description="Get the content of a specific Wikipedia page by title. Returns page content, URL, and metadata."
)
async def get_page_content(
    title: str = Field(description="Wikipedia page title")
) -> str:
    """获取指定Wikipedia页面的内容"""
    async with WikipediaCrawler() as crawler:
        content = await crawler.get_page_content(title)
    return json.dumps(content, ensure_ascii=False, indent=2)


@wikipedia_tools.tool(
    description="Crawl multiple Wikipedia pages based on search queries. Returns a collection of page contents for auto-categorization."
)
async def crawl_wikipedia_pages(
    queries: List[str] = Field(description="List of search queries to cover different subtopics"),
    max_pages: int = Field(description="Maximum total number of pages to crawl (e.g., 50)"),
    pages_per_query: int = Field(description="Maximum pages per query", default=5)
) -> str:
    """批量爬取Wikipedia页面"""
    all_pages: List[Dict[str, Any]] = []
    seen_titles = set()

    async with WikipediaCrawler() as crawler:
        # 先收集候选标题，再并发抓取，显著缩短整体耗时。
        candidate_titles: List[str] = []
        for query in queries:
            if len(candidate_titles) >= max_pages * 2:
                break

            remaining = max_pages - len(candidate_titles)
            limit = min(pages_per_query, max(1, remaining))

            print(f"Searching: '{query}' (limit: {limit})")
            search_results = await crawler.search_pages(query, limit)

            for result in search_results:
                if "error" in result:
                    continue

                title = result["title"]
                if title in seen_titles:
                    continue

                seen_titles.add(title)
                candidate_titles.append(title)
                if len(candidate_titles) >= max_pages:
                    break

            if len(candidate_titles) >= max_pages:
                break

        semaphore = asyncio.Semaphore(6)

        async def fetch_one(title: str) -> Dict[str, Any]:
            async with semaphore:
                print(f"  Fetching: {title}")
                return await crawler.get_page_content(title)

        tasks = [asyncio.create_task(fetch_one(title)) for title in candidate_titles[:max_pages]]

        for task in asyncio.as_completed(tasks):
            page_content = await task
            if "error" not in page_content:
                all_pages.append(page_content)
                print(f"  ✓ Collected ({len(all_pages)}/{max_pages})")
            else:
                print(f"  ✗ Failed: {page_content.get('error')}")

            if len(all_pages) >= max_pages:
                break
    
    return json.dumps({
        "total_crawled": len(all_pages),
        "unique_pages": len(all_pages),
        "pages": all_pages
    }, ensure_ascii=False, indent=2)


# ============================================
# 本地保存工具 - 按分类保存
# ============================================

def _sanitize_filename(name: str) -> str:
    """清理文件名"""
    # 替换非法字符
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 限制长度
    return safe[:100]


def _sanitize_folder_name(name: str) -> str:
    """清理文件夹名称"""
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    return safe[:80]


@file_tools.tool(
    description="Save page content to a category folder. Creates folder structure automatically."
)
def save_page_to_category(
    domain: str = Field(description="Domain name (e.g., 'Computer Science')"),
    category: str = Field(description="Category name for folder organization"),
    title: str = Field(description="Page title"),
    content: str = Field(description="Page content to save"),
    url: str = Field(description="Original URL"),
    metadata: Dict[str, Any] = Field(
        description="Additional metadata (summary, key_concepts, etc.)",
        default_factory=dict
    ),
    file_format: str = Field(description="File format: 'md' or 'txt'", default="md")
    ) -> str:
    return _save_page_to_category_impl(
        domain=domain,
        category=category,
        title=title,
        content=content,
        url=url,
        metadata=metadata,
        file_format=file_format,
    )


def _save_page_to_category_impl(
    domain: str,
    category: str,
    title: str,
    content: str,
    url: str,
    metadata: Dict[str, Any],
    file_format: str,
) -> str:
    """
    将页面内容保存到分类文件夹
    
    文件夹结构: output/content/{domain}/{category}/{title}.md
    """
    try:
        config = get_config()
        
        # 构建文件夹路径
        safe_domain = _sanitize_folder_name(domain)
        safe_category = _sanitize_folder_name(category)
        safe_title = _sanitize_filename(title)
        
        category_dir = os.path.join(config.content_dir, safe_domain, safe_category)
        os.makedirs(category_dir, exist_ok=True)
        
        # 构建文件路径
        ext = file_format if file_format in ["md", "txt"] else "md"
        file_path = os.path.join(category_dir, f"{safe_title}.{ext}")
        
        # 获取语言文本
        t_title = config.get_text("title")
        t_url = config.get_text("url")
        t_summary = config.get_text("summary")
        t_key_concepts = config.get_text("key_concepts")
        
        # 构建文件内容
        if file_format == "md":
            # Markdown格式
            md_content = f"# {title}\n\n"
            md_content += f"**{t_url}:** {url}\n\n"
            
            if metadata.get("summary"):
                md_content += f"## {t_summary}\n\n{metadata['summary']}\n\n"
            
            if metadata.get("key_concepts"):
                concepts = metadata["key_concepts"]
                if isinstance(concepts, list):
                    md_content += f"## {t_key_concepts}\n\n"
                    for concept in concepts:
                        md_content += f"- {concept}\n"
                    md_content += "\n"
            
            md_content += "---\n\n"
            md_content += content
            
            file_content = md_content
        else:
            # 纯文本格式
            txt_content = f"{t_title}: {title}\n"
            txt_content += f"{t_url}: {url}\n"
            txt_content += f"\n{'='*50}\n\n"
            txt_content += content
            file_content = txt_content
        
        # 保存文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        return f"Saved page to: {file_path}"
        
    except Exception as e:
        return f"Error saving page: {str(e)}"


@file_tools.tool(
    description="Generate a Markdown index file for categorized content. Supports multiple languages."
)
def generate_markdown_index(
    domain: str = Field(description="Domain name"),
    categories: List[Dict[str, Any]] = Field(description="List of categories with pages"),
    total_pages: int = Field(description="Total number of pages"),
    index_summary: str = Field(description="Overall summary of the index"),
    uncategorized: List[Dict[str, Any]] = Field(description="Uncategorized pages", default_factory=list),
    category_relations: List[Dict[str, str]] = Field(description="Relations between categories", default_factory=list),
    language: str = Field(description="Language code: 'zh' or 'en'", default="zh")
) -> str:
    return _generate_markdown_index_impl(
        domain=domain,
        categories=categories,
        total_pages=total_pages,
        index_summary=index_summary,
        uncategorized=uncategorized,
        category_relations=category_relations,
        language=language,
    )


def _generate_markdown_index_impl(
    domain: str,
    categories: List[Dict[str, Any]],
    total_pages: int,
    index_summary: str,
    uncategorized: List[Dict[str, Any]],
    category_relations: List[Dict[str, str]],
    language: str,
) -> str:
    """
    生成Markdown格式的索引文件
    
    输出路径: output/index/{domain}_index.md
    """
    try:
        config = get_config()
        config.language = language
        
        # 确保索引目录存在
        index_dir = config.index_dir
        os.makedirs(index_dir, exist_ok=True)
        
        # 构建文件路径
        safe_domain = _sanitize_folder_name(domain)
        index_path = os.path.join(index_dir, f"{safe_domain}_index.md")
        
        # 获取语言文本
        t_title = config.get_text("md_title_template").format(domain=domain)
        t_overview = config.get_text("md_overview")
        t_category = config.get_text("categories")
        t_total = config.get_text("total_pages")
        t_page_count = config.get_text("page_count")
        t_url = config.get_text("url")
        t_summary = config.get_text("summary")
        t_key_concepts = config.get_text("key_concepts")
        t_uncategorized = config.get_text("md_uncategorized")
        t_relations = config.get_text("md_category_relations")
        t_footer = config.get_text("md_footer")
        
        # 构建Markdown内容
        md_lines = []
        
        # 标题
        md_lines.append(f"# {t_title}")
        md_lines.append("")
        md_lines.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        md_lines.append("")
        
        # 概述
        md_lines.append(f"## {t_overview}")
        md_lines.append("")
        md_lines.append(f"- **{t_total}:** {total_pages}")
        md_lines.append(f"- **{t_category}:** {len(categories)}")
        md_lines.append("")
        md_lines.append(index_summary)
        md_lines.append("")
        
        # 目录
        md_lines.append("## 目录")
        md_lines.append("")
        for i, cat in enumerate(categories, 1):
            cat_name = cat.get("category_name", f"Category {i}")
            page_count = cat.get("page_count", len(cat.get("pages", [])))
            md_lines.append(f"{i}. [{cat_name}](#{cat_name.lower().replace(' ', '-')}) - {page_count} pages")
        if uncategorized:
            md_lines.append(f"{len(categories)+1}. [{t_uncategorized}](#uncategorized)")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # 各分类详情
        for cat in categories:
            cat_name = cat.get("category_name", "Unknown")
            cat_desc = cat.get("description", "")
            pages = cat.get("pages", [])
            
            md_lines.append(f"## 📁 {cat_name}")
            md_lines.append("")
            if cat_desc:
                md_lines.append(f"*{cat_desc}*")
                md_lines.append("")
            md_lines.append(f"**{t_page_count}:** {len(pages)}")
            md_lines.append("")
            
            # 页面列表
            for page in pages:
                title = page.get("title", "Unknown")
                url = page.get("url", "")
                summary = page.get("summary", "")
                
                md_lines.append(f"### {title}")
                md_lines.append("")
                if url:
                    md_lines.append(f"- **{t_url}:** [{url}]({url})")
                if summary:
                    md_lines.append(f"- **{t_summary}:** {summary}")
                if page.get("key_concepts"):
                    concepts = page["key_concepts"]
                    if isinstance(concepts, list) and concepts:
                        md_lines.append(f"- **{t_key_concepts}:** {', '.join(str(c) for c in concepts)}")
                md_lines.append("")
            
            md_lines.append("---")
            md_lines.append("")
        
        # 未分类页面
        if uncategorized:
            md_lines.append(f"## {t_uncategorized}")
            md_lines.append("")
            for page in uncategorized:
                title = page.get("title", "Unknown")
                reason = page.get("reason", "")
                md_lines.append(f"- **{title}** - {reason}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        # 分类关系
        if category_relations:
            md_lines.append(f"## {t_relations}")
            md_lines.append("")
            for rel in category_relations:
                cat_a = rel.get("category_a", "")
                cat_b = rel.get("category_b", "")
                relation = rel.get("relation", "")
                if cat_a and cat_b:
                    md_lines.append(f"- **{cat_a}** ↔️ **{cat_b}**: {relation}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        # 页脚
        md_lines.append(f"\n*{t_footer}*")
        
        # 保存文件
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        
        return f"Generated Markdown index: {index_path}"
        
    except Exception as e:
        return f"Error generating index: {str(e)}"


@file_tools.tool(
    description="Save categorized content to local folders and generate Markdown index." 
)
def save_categorized_content(
    domain: str = Field(description="Domain name"),
    categorized_data: Dict[str, Any] = Field(description="Complete categorized data from clustering_agent"),
    language: str = Field(description="Language code: 'zh' or 'en'", default="zh")
) -> str:
    """
    保存分类内容到本地文件夹并生成Markdown索引
    
    Args:
        domain: 领域名称
        categorized_data: clustering_agent生成的完整分类数据
        language: 语言代码，"zh"为简体中文，"en"为英文
    
    Returns:
        操作结果描述
    """
    try:
        config = get_config()
        config.language = language
        
        results = []
        
        # 1. 保存每个页面到分类文件夹
        categories = categorized_data.get("auto_generated_categories", [])
        
        for cat in categories:
            cat_name = cat.get("category_name", "Uncategorized")
            pages = cat.get("pages", [])
            
            for page in pages:
                title = page.get("title", "Untitled")
                content = page.get("content", "")
                url = page.get("url", "")
                
                # 构建元数据
                metadata = {
                    "summary": page.get("summary", ""),
                    "key_concepts": page.get("key_concepts", []),
                    "relevance_score": page.get("relevance_score", 0),
                }
                
                # 保存到分类文件夹
                result = _save_page_to_category_impl(
                    domain=domain,
                    category=cat_name,
                    title=title,
                    content=content,
                    url=url,
                    metadata=metadata,
                    file_format="md"
                )
                results.append(result)
        
        # 2. 生成Markdown索引
        index_result = _generate_markdown_index_impl(
            domain=domain,
            categories=categories,
            total_pages=categorized_data.get("total_pages", 0),
            index_summary=categorized_data.get("index_summary", ""),
            uncategorized=categorized_data.get("uncategorized_pages", []),
            category_relations=categorized_data.get("category_relations", []),
            language=language
        )
        results.append(index_result)
        
        # 3. 保存原始JSON数据
        output_dir = config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"{_sanitize_filename(domain)}_data.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(categorized_data, f, ensure_ascii=False, indent=2)
        results.append(f"Saved JSON data: {json_path}")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"Error saving categorized content: {str(e)}"


# ============================================
# 基础文件操作工具
# ============================================

@file_tools.tool(
    description="Save content to a JSON file. Creates directories if needed."
)
def save_json(
    path: str = Field(description="File path to save the JSON content"),
    content: Dict[str, Any] = Field(description="Dictionary content to save as JSON")
) -> str:
    """保存JSON内容到文件"""
    try:
        dir_path = os.path.dirname(os.path.abspath(path))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        return f"Successfully saved JSON to {path}"
    except Exception as e:
        return f"Error saving file: {str(e)}"


@file_tools.tool(
    description="Read content from a JSON file."
)
def read_json(
    path: str = Field(description="Path to the JSON file to read")
) -> str:
    """读取JSON文件内容"""
    try:
        if not os.path.exists(path):
            return json.dumps({"error": f"File not found: {path}"})
        
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
        
        return json.dumps(content, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@file_tools.tool(
    description="Read text content from a file."
)
def read_text(
    path: str = Field(description="Path to the text file to read")
) -> str:
    """读取文本文件内容"""
    try:
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
