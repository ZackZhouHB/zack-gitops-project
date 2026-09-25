# Archive: Joe's writing

Joe's 20 posts (Feb 2021: stories, book and movie reviews, "Saving The Planet" series) from the original Django blog. They are kept here for safekeeping and are **not published**. Hugo only builds `content/` and `static/`, so nothing in `archive/` appears on the site, in search, or as a public image URL.

```
archive/joe/
├── posts/        # 20 Markdown posts (front matter intact: title, date, slug, aliases)
└── images/joe/   # 30 images the posts reference as /images/joe/...
```

## Republish

All posts at once:

```bash
cd blog-site
git mv archive/joe/images/joe static/images/joe
git mv archive/joe/posts/*.md content/posts/
```

A single post: move the `.md` file to `content/posts/`, plus the images it uses (`grep -o '/images/joe/[^)]*' <file>`) into `static/images/joe/`.

Preview with `hugo server`, then commit and push to `editing`. The pipeline's link check fails if an image was left behind. Old links (`/post/<id>/`) come back automatically through each post's `aliases`.
