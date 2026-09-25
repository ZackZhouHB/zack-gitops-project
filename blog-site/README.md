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

Each post is a folder (a Hugo "page bundle") with its text and images together:

```
content/posts/eks-cost-tuning/
├── index.md        # the post
├── diagram.png     # images live next to it
└── result.png
```

```bash
cd blog-site
git pull                                          # 1. sync
hugo new content posts/eks-cost-tuning/index.md   # 2. create (draft: true)
hugo server -D                                    # 3. preview at http://localhost:1313 (live reload)
#    edit index.md; drop or paste images into the folder; reference as ![alt](diagram.png)
#    set draft: false when ready
git add content/posts/eks-cost-tuning             # 4. publish
git commit -m "post: EKS cost tuning"
git push                                          # 5. GitHub Actions builds, checks links, deploys (~1 min)
```

- Front matter: `title`, `date`, `draft`, `categories` (AWS, Kubernetes, DevOps, Machine Learning, Python, General), optional `slug`.
- The URL is `/posts/<slug>/`. The slug defaults to the title, e.g. `/posts/eks-cost-tuning/`.
- `draft: true` posts only show with `hugo server -D`. They are never published.
- VS Code: pasting an image into `index.md` saves it into the same folder automatically.
- Legacy posts are single files in `content/posts/` with images in `static/images/` (`/images/...`). Both styles work.
- Optional review flow: push a branch and open a PR. CI builds and link-checks it; merging deploys it.

## Local development

```bash
git submodule update --init --recursive    # fetch the theme
brew install hugo lychee
hugo server -D                             # live reload, drafts included
# same link check as CI:
hugo --gc --baseURL / -d public-check && lychee --offline --root-dir "$PWD/public-check" 'public-check/**/*.html'; rm -rf public-check
```

A lightweight blog-only checkout (no need for the rest of the monorepo):

```bash
git clone --filter=blob:none --sparse git@github.com:ZackZhouHB/zack-gitops-project.git zackblog
cd zackblog && git sparse-checkout set blog-site .github
git submodule update --init blog-site/themes/PaperMod
```

## Migration from Django

`tools/export_from_django.py` converted the 92 legacy posts from the Django SQLite DB to Markdown:

- `<pre>` blocks are extracted verbatim, then turned into fenced code blocks with a guessed language.
- The rest is rendered with python-markdown (same as django-markdownx), then converted with markdownify.
- Legacy URLs `/post/<id>/` redirect to the new `/posts/<slug>/` via Hugo `aliases`.
- Django authors (`zack-aws`, `zack-kubernetes`, ...) became categories.
- Joe's 20 posts are archived (kept in git, not published) in [`archive/joe/`](archive/joe/README.md).

Re-run (one-off, overwrites exported posts):

```bash
pip install -r tools/requirements.txt
python tools/export_from_django.py --db ../django_project/db.sqlite3 --out content/posts
```
