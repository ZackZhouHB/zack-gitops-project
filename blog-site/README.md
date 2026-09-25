# Zack's Blog: Hugo + GitHub Actions + GitHub Pages

Source for [zackblog.work](https://zackblog.work). It is a static site built with [Hugo](https://gohugo.io/) and the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme, and deployed to GitHub Pages by GitHub Actions.

It replaces the earlier Django + Docker + EC2 version (`../django_project/`).

## Architecture

```
content/posts/*.md ──git push──▶ GitHub Actions ──▶ GitHub Pages ──▶ zackblog.work
                                 │ hugo build                        (Cloudflare DNS)
                                 │ lychee link check
                                 └ deploy (editing branch only)
```

- Workflow: [`.github/workflows/hugo-pages.yaml`](../.github/workflows/hugo-pages.yaml)
- Pull requests build and link-check only. Pushes to `editing` also deploy.
- No servers, containers or databases. Hosting is free and HTTPS is automatic.

## Write a new post

```bash
cd blog-site
hugo new content posts/my-new-post.md      # created as draft
# put images in static/images/ and reference them as ![alt](/images/name.png)
hugo server -D                             # preview at http://localhost:1313
# set draft: false, then commit and push to editing
```

Front matter fields: `title`, `date`, `categories` (AWS, Kubernetes, DevOps, Machine Learning, Python, General, Joe's Corner), optional `slug`.

## Local development

```bash
git submodule update --init --recursive    # fetch the theme
brew install hugo lychee
hugo server                                # live reload
hugo --gc --baseURL / -d public-check && lychee --offline --root-dir "$PWD/public-check" 'public-check/**/*.html'
```

## Migration from Django

`tools/export_from_django.py` converted the 92 legacy posts from the Django SQLite DB to Markdown:

- `<pre>` blocks are extracted verbatim, then turned into fenced code blocks with a guessed language.
- The rest is rendered with python-markdown (same as django-markdownx), then converted with markdownify.
- Legacy URLs `/post/<id>/` redirect to the new `/posts/<slug>/` via Hugo `aliases`.
- Django authors (`zack-aws`, `zack-kubernetes`, ...) became categories.

Re-run (one-off, overwrites exported posts):

```bash
pip install -r tools/requirements.txt
python tools/export_from_django.py --db ../django_project/db.sqlite3 --out content/posts
```
