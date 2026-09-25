#!/usr/bin/env python3
"""Export posts from the legacy Django blog (SQLite) to Hugo Markdown.

Usage:
    pip install -r tools/requirements.txt
    python tools/export_from_django.py --db ../django_project/db.sqlite3 --out content/posts

Pipeline per post:
  1. Pull <pre> blocks out verbatim (they contain raw text such as `<none>`
     that an HTML parser would swallow) and replace them with placeholders.
  2. Render the remaining Markdown+HTML with python-markdown, the same engine
     django-markdownx used on the live site.
  3. Convert the resulting HTML to Markdown with markdownify.
  4. Put the code blocks back as fenced blocks with a best-guess language.
"""

import argparse
import html
import json
import re
import sqlite3
import textwrap
from pathlib import Path

import markdown
from markdownify import MarkdownConverter

AUTHOR_CATEGORY = {
    "zackz": "General",
    "zack-aws": "AWS",
    "zack-python": "Python",
    "zack-devops": "DevOps",
    "zack-machine-learning": "Machine Learning",
    "zack-kubernetes": "Kubernetes",
    "joez": "Joe's Corner",
}

PRE_RE = re.compile(r"<pre\b[^>]*>(.*?)</pre>", re.S | re.I)
CODE_OPEN_RE = re.compile(r"^\s*<code\b([^>]*)>", re.I)
CODE_CLOSE_RE = re.compile(r"</code>\s*$", re.I)
PLACEHOLDER = "ZZPRE{:04d}ZZ"
PLACEHOLDER_RE = re.compile(r"ZZPRE(\d{4})ZZ")
OLD_POST_URL_RE = re.compile(r"https?://(?:www\.)?zackblog\.work/post/(\d+)/?")
SHELL_LINE_RE = re.compile(
    r"^\s*(\$ |# |sudo |kubectl |aws |docker |git |cd |ls\b|cat |vim? |curl |helm |terraform |pip3? |python3? "
    r"|npm |export |echo |mkdir |chmod |systemctl |apt(-get)? |yum |dnf |brew |eksctl |ssh |scp |wget |ansible"
    r"|argocd |minikube |kind |k |source |cp |mv |rm |touch |openssl |nano |make |\S+@\S+?:\S*\s?[#$] )",
    re.M,
)


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:80].rstrip("-") or "post"


def guess_lang(code: str, hint: str) -> str:
    m = re.search(r'class="([a-z0-9+-]+)"', hint or "")
    if m:
        return m.group(1)
    head = code.lstrip()[:400]
    if re.search(r"^(apiVersion|kind):", code, re.M):
        return "yaml"
    if re.search(r'^\s*(resource|module|variable|provider|terraform|output|data)\s+("|\{)', code, re.M):
        return "hcl"
    if re.match(r"FROM\s+\S+", head):
        return "dockerfile"
    if head.startswith(("{", "[")) and head.rstrip().endswith(("}", "]")):
        return "json"
    if re.search(r"^\s*(def |class |import |from \S+ import )", code, re.M):
        return "python"
    if SHELL_LINE_RE.search(code):
        return "bash"
    return "text"


def extract_pre_blocks(text: str):
    blocks = []

    def repl(m):
        inner = m.group(1)
        hint = ""
        om = CODE_OPEN_RE.match(inner)
        if om:
            hint = om.group(1)
            inner = CODE_CLOSE_RE.sub("", inner[om.end():])
        inner = html.unescape(inner)
        lines = inner.split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        code = textwrap.dedent("\n".join(l.rstrip() for l in lines))
        blocks.append((code, guess_lang(code, hint)))
        return "\n\n" + PLACEHOLDER.format(len(blocks) - 1) + "\n\n"

    return PRE_RE.sub(repl, text), blocks


class BlogConverter(MarkdownConverter):
    """markdownify, keeping a few inline tags as HTML (Hugo renders them in unsafe mode)."""

    def _keep(self, tag, text):
        return f"<{tag}>{text.strip()}</{tag}>" if text.strip() else ""

    def convert_mark(self, el, text, *args, **kwargs):
        return self._keep("mark", text)

    def convert_ins(self, el, text, *args, **kwargs):
        return self._keep("ins", text)

    def convert_img(self, el, text, *args, **kwargs):
        el["src"] = re.sub(r"\s+", "", el.get("src", ""))
        return super().convert_img(el, text, *args, **kwargs)

    def convert_a(self, el, text, *args, **kwargs):
        if el.get("href"):
            el["href"] = re.sub(r"\s+", "", el["href"])
        return super().convert_a(el, text, *args, **kwargs)


def to_markdown(html_text: str) -> str:
    return BlogConverter(heading_style="ATX", bullets="-").convert(html_text)


def restore_pre_blocks(md: str, blocks) -> str:
    out = []
    for line in md.split("\n"):
        m = PLACEHOLDER_RE.search(line)
        if not m:
            out.append(line)
            continue
        code, lang = blocks[int(m.group(1))]
        before, after = line[: m.start()], line[m.end():]
        indent = ""
        if re.fullmatch(r"\s*([-*+]|\d+\.)\s*", before):
            out.append(before.rstrip())
            indent = " " * len(before)
        elif before.strip():
            out.append(before.rstrip())
        else:
            indent = before
        fence = "````" if "```" in code else "```"
        out.append("")
        out.append(f"{indent}{fence}{lang}")
        out.extend(f"{indent}{l}" if l else "" for l in code.split("\n"))
        out.append(f"{indent}{fence}")
        out.append("")
        if after.strip():
            out.append(after.strip())
    return "\n".join(out)


def clean_source(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Some posts were pasted from the old Jekyll site with their front matter still attached.
    text = re.sub(r"\A\s*---\s*\n(?:\s*(?:date|categories|layout|title):.*\n|\s*\n)*\s*---\s*\n", "", text)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<meta\b[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    # Keep an HTML wrapper so indented markup after it is not parsed as a Markdown code block.
    text = re.sub(r"<(/?)(html|head|body)\b[^>]*>", r"<\1div>", text, flags=re.I)
    return text


def convert(content: str, permalinks: dict) -> str:
    text, blocks = extract_pre_blocks(clean_source(content))
    md = to_markdown(markdown.markdown(text))
    md = restore_pre_blocks(md, blocks)
    md = OLD_POST_URL_RE.sub(lambda m: permalinks.get(int(m.group(1)), m.group(0)), md)
    md = md.replace("/static/blog/images/", "/images/")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    rows = conn.execute(
        "SELECT p.id, p.title, p.content, p.date_posted, u.username "
        "FROM blog_post p JOIN auth_user u ON u.id = p.author_id ORDER BY p.id"
    ).fetchall()

    slugs = {pid: slugify(title) for pid, title, *_ in rows}
    permalinks = {pid: f"/posts/{slug}/" for pid, slug in slugs.items()}

    for pid, title, content, date_posted, username in rows:
        date = date_posted.replace(" ", "T")[:19] + "Z"
        front = [
            "---",
            f"title: {json.dumps(title.strip(), ensure_ascii=False)}",
            f"date: {date}",
            f"slug: {slugs[pid]}",
            f"categories: [{json.dumps(AUTHOR_CATEGORY.get(username, 'General'))}]",
            f'aliases: ["/post/{pid}/"]',
            f"legacy_id: {pid}",
            "---",
            "",
        ]
        path = out / f"{pid:03d}-{slugs[pid]}.md"
        path.write_text("\n".join(front) + convert(content, permalinks), encoding="utf-8")

    print(f"Exported {len(rows)} posts to {out}")


if __name__ == "__main__":
    main()
