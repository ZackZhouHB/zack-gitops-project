"""Web/Blog Loader - Scrape blog posts for RAG ingestion"""
import io
import re
import logging
from typing import List, Optional
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup

from .base import LoadedDocument

logger = logging.getLogger(__name__)


@dataclass
class BlogPost:
    """Represents a single blog post"""
    url: str
    title: str
    content: str
    author: Optional[str] = None
    date: Optional[str] = None
    tags: Optional[List[str]] = None


class WebLoader:
    """
    Load content from web pages.
    Supports generic HTML and blog-specific extraction.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def load_url(self, url: str) -> LoadedDocument:
        """Load a single URL and extract text content"""
        resp = self.client.get(url)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else url
        
        # Get main content
        main = soup.find('main') or soup.find('article') or soup.find('body')
        content = main.get_text(separator='\n', strip=True) if main else ""
        
        return LoadedDocument(
            content=f"# {title_text}\n\n{content}",
            filename=url,
            source_type="web",
            size_bytes=len(resp.content),
            checksum=LoadedDocument.calculate_checksum(resp.content),
            metadata={"url": url, "title": title_text}
        )
    
    def load_blog_post(self, post_url: str) -> LoadedDocument:
        """Load a Django blog post with structured extraction"""
        if not post_url.startswith("http"):
            post_url = f"{self.base_url}{post_url}"
        
        resp = self.client.get(post_url)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h2', class_='article-title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "Untitled"
        
        # Extract author and date
        metadata = soup.find('div', class_='article-metadata')
        author = None
        date = None
        if metadata:
            author_link = metadata.find('a')
            author = author_link.get_text().strip() if author_link else None
            date_elem = metadata.find('small')
            date = date_elem.get_text().strip() if date_elem else None
        
        # Extract tags
        tags_elem = soup.find('p', class_='tech-tags-text')
        tags = []
        if tags_elem:
            tags = [t.strip() for t in tags_elem.get_text().split('##') if t.strip()]
        
        # Extract main content - look for article body
        content_elem = soup.find('div', class_='article-content') or soup.find('article')
        if content_elem:
            # Remove nested metadata
            for meta in content_elem.find_all(['div', 'p'], class_=['article-metadata', 'tech-tags-text']):
                meta.decompose()
            content = content_elem.get_text(separator='\n', strip=True)
        else:
            content = ""
        
        # Build structured document
        doc_content = f"""# {title}

**Author:** {author or 'Unknown'}
**Date:** {date or 'Unknown'}
**Tags:** {', '.join(tags) if tags else 'None'}

---

{content}
"""
        
        logger.info(f"Loaded blog post: {title}, {len(content)} chars")
        
        return LoadedDocument(
            content=doc_content,
            filename=post_url,
            source_type="blog",
            size_bytes=len(resp.content),
            checksum=LoadedDocument.calculate_checksum(resp.content),
            metadata={
                "url": post_url,
                "title": title,
                "author": author,
                "date": date,
                "tags": tags
            }
        )
    
    def discover_blog_posts(self, max_posts: int = 50) -> List[str]:
        """Discover blog post URLs from the homepage"""
        resp = self.client.get(self.base_url)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all post links
        post_urls = []
        for link in soup.find_all('a', class_='article-title'):
            href = link.get('href')
            if href and '/post/' in href:
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"
                post_urls.append(href)
        
        # Also check for pagination
        # Look for links like /post/123/
        for link in soup.find_all('a', href=True):
            href = link['href']
            if re.match(r'^/post/\d+/?$', href):
                full_url = f"{self.base_url}{href}"
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
        logger.info(f"Discovered {len(post_urls)} blog posts")
        return post_urls[:max_posts]
    
    def load_all_posts(self, max_posts: int = 50) -> List[LoadedDocument]:
        """Load all blog posts"""
        urls = self.discover_blog_posts(max_posts)
        documents = []
        
        for url in urls:
            try:
                doc = self.load_blog_post(url)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load {url}: {e}")
        
        return documents
