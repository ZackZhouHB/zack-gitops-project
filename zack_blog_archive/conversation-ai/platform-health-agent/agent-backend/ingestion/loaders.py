"""Document loaders — fetch content from blog, Confluence, and local files.

Each loader returns a list of Document dicts:
    {"title": str, "content": str, "source": str, "url": str, "source_type": str}
"""

import os
import json
import re
from html.parser import HTMLParser

import requests
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Helper: Strip HTML tags to plain text
# ---------------------------------------------------------------------------
class HTMLStripper(HTMLParser):
    """Simple HTML tag stripper — converts HTML to plain text."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = False
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self.result.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.result.append(data)


def strip_html(html: str) -> str:
    """Convert HTML to clean plain text."""
    stripper = HTMLStripper()
    stripper.feed(html)
    text = "".join(stripper.result)
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Loader 1: Blog posts from zackblog.work
# ---------------------------------------------------------------------------
def load_blog_posts() -> list[dict]:
    """Crawl blog posts from zackblog.work.
    
    Process:
    1. Fetch the homepage to find all post URLs
    2. Fetch each post page
    3. Extract the main content (strip HTML)
    4. Return as Document dicts
    """
    blog_url = os.getenv("BLOG_URL", "https://zackblog.work/")
    documents = []

    # Find all post URLs from homepage
    try:
        resp = requests.get(blog_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"   ⚠️  Failed to fetch blog homepage: {e}")
        return documents

    # Extract post URLs like /post/156/
    post_paths = list(set(re.findall(r'href="(/post/\d+/)"', resp.text)))
    post_paths.sort()

    print(f"   Found {len(post_paths)} blog posts")

    for path in post_paths:
        url = blog_url.rstrip("/") + path
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()

            # Extract title from <h2> or <title>
            title_match = re.search(r"<h[12][^>]*>(.*?)</h[12]>", resp.text, re.DOTALL)
            title = strip_html(title_match.group(1)) if title_match else f"Blog Post {path}"

            # Extract main content
            content = strip_html(resp.text)

            if len(content) > 100:  # Skip empty pages
                documents.append({
                    "title": title,
                    "content": content,
                    "source": f"blog{path}",
                    "url": url,
                    "source_type": "blog",
                })
                print(f"   ✅ {title[:60]}...")

        except Exception as e:
            print(f"   ⚠️  Failed to fetch {url}: {e}")

    return documents


# ---------------------------------------------------------------------------
# Loader 2: Confluence pages via Atlassian REST API
# ---------------------------------------------------------------------------
def load_confluence_pages() -> list[dict]:
    """Fetch Confluence pages under the configured parent page.
    
    Process:
    1. Use the Atlassian REST API with Basic Auth (email + API token)
    2. Fetch all child pages of the parent page
    3. For each page, fetch the body in 'storage' format (HTML)
    4. Strip HTML to plain text
    5. Return as Document dicts
    """
    base_url = os.getenv("CONFLUENCE_URL", "")
    parent_id = os.getenv("CONFLUENCE_PARENT_PAGE_ID", "")
    username = os.getenv("CONFLUENCE_USERNAME", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")

    if not all([base_url, parent_id, username, api_token]):
        print("   ⚠️  Confluence credentials not configured. Skipping.")
        return []

    auth = (username, api_token)
    documents = []

    # Fetch child pages of parent
    try:
        resp = requests.get(
            f"{base_url}/wiki/rest/api/content/{parent_id}/child/page",
            auth=auth,
            params={"limit": 50, "expand": "body.storage"},
            timeout=30,
        )
        resp.raise_for_status()
        pages = resp.json().get("results", [])
    except Exception as e:
        print(f"   ⚠️  Failed to fetch Confluence pages: {e}")
        return documents

    print(f"   Found {len(pages)} Confluence pages")

    for page in pages:
        title = page.get("title", "Untitled")
        page_id = page.get("id", "")
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        content = strip_html(html_body)

        if len(content) > 100:
            url = f"{base_url}/wiki/spaces/ET/pages/{page_id}"
            documents.append({
                "title": title,
                "content": content,
                "source": f"confluence/{page_id}",
                "url": url,
                "source_type": "confluence",
            })
            print(f"   ✅ {title[:60]}...")

    return documents


# ---------------------------------------------------------------------------
# Loader 3: Local files (PDF and Markdown)
# ---------------------------------------------------------------------------
def load_local_files() -> list[dict]:
    """Load documents from the ./documents/ folder.
    
    Supports:
    - .md files: Read as plain text
    - .pdf files: Extract text using a simple PDF text extractor
    - .txt files: Read as plain text
    """
    docs_dir = os.getenv("DOCUMENTS_DIR", "/app/documents")

    # Also check local path for development outside Docker
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "documents")

    if not os.path.exists(docs_dir):
        print(f"   ⚠️  Documents directory not found: {docs_dir}")
        return []

    documents = []

    for filename in sorted(os.listdir(docs_dir)):
        filepath = os.path.join(docs_dir, filename)

        if not os.path.isfile(filepath):
            continue

        content = ""
        if filename.endswith(".md") or filename.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        elif filename.endswith(".pdf"):
            content = extract_pdf_text(filepath)

        else:
            print(f"   ⏭️  Skipping unsupported file: {filename}")
            continue

        if len(content) > 100:
            documents.append({
                "title": filename,
                "content": content,
                "source": f"file/{filename}",
                "url": f"local://{filename}",
                "source_type": "file",
            })
            print(f"   ✅ {filename} ({len(content)} chars)")

    return documents


def extract_pdf_text(filepath: str) -> str:
    """Extract text from a PDF file.
    
    Uses PyPDF2 if available, falls back to a basic binary extraction.
    """
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except ImportError:
        print(f"   ⚠️  PyPDF2 not installed. Skipping PDF: {filepath}")
        return ""
    except Exception as e:
        print(f"   ⚠️  Failed to read PDF {filepath}: {e}")
        return ""
