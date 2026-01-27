"""Enterprise Web Connector - Scrapes internal websites with authentication"""
import httpx
import re
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

@dataclass
class WebPage:
    url: str
    title: str
    content: str
    content_hash: str
    metadata: Dict

class WebConnector:
    """Connector for internal company websites (Django, WordPress, etc.)"""
    
    def __init__(self, base_url: str, auth_config: Optional[Dict] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_config = auth_config or {}
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.session_cookie = None
    
    def authenticate(self) -> bool:
        """Authenticate with the website (supports Django admin, basic auth, API key)"""
        auth_type = self.auth_config.get("type", "none")
        
        if auth_type == "django_admin":
            return self._django_auth()
        elif auth_type == "basic":
            self.client.auth = (self.auth_config["username"], self.auth_config["password"])
            return True
        elif auth_type == "api_key":
            self.client.headers["Authorization"] = f"Bearer {self.auth_config['api_key']}"
            return True
        elif auth_type == "cookie":
            self.client.cookies.set(self.auth_config["cookie_name"], self.auth_config["cookie_value"])
            return True
        return True  # No auth needed
    
    def _django_auth(self) -> bool:
        """Django session authentication"""
        login_url = f"{self.base_url}/admin/login/"
        
        # Get CSRF token
        resp = self.client.get(login_url)
        csrf = self._extract_csrf(resp.text)
        if not csrf:
            logger.error("Failed to get CSRF token")
            return False
        
        # Login
        resp = self.client.post(login_url, data={
            "username": self.auth_config["username"],
            "password": self.auth_config["password"],
            "csrfmiddlewaretoken": csrf,
            "next": "/admin/"
        }, headers={"Referer": login_url})
        
        return "sessionid" in self.client.cookies
    
    def _extract_csrf(self, html: str) -> Optional[str]:
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        return match.group(1) if match else None
    
    def discover_pages(self, pattern: str = "/post/") -> List[str]:
        """Discover all pages matching pattern"""
        resp = self.client.get(self.base_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        urls = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if pattern in href:
                full_url = urljoin(self.base_url, href)
                urls.add(full_url)
        
        return sorted(urls)
    
    def fetch_page(self, url: str) -> Optional[WebPage]:
        """Fetch and parse a single page"""
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string or ""
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
            
            # Extract main content (try common patterns)
            content = ""
            for selector in ['article', '.article-content', '.post-content', '.entry-content', 'main', '.content']:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(separator='\n', strip=True)
                    break
            
            if not content:
                # Fallback: get body text minus nav/footer
                for tag in soup(['nav', 'footer', 'header', 'script', 'style']):
                    tag.decompose()
                content = soup.get_text(separator='\n', strip=True)
            
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            return WebPage(
                url=url,
                title=title,
                content=content,
                content_hash=content_hash,
                metadata={"source_type": "web", "base_url": self.base_url}
            )
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def fetch_all(self, pattern: str = "/post/", limit: int = 50) -> List[WebPage]:
        """Fetch all pages matching pattern"""
        urls = self.discover_pages(pattern)[:limit]
        pages = []
        
        for url in urls:
            page = self.fetch_page(url)
            if page and page.content:
                pages.append(page)
                logger.info(f"Fetched: {page.title[:50]}")
        
        return pages
    
    def close(self):
        self.client.close()
