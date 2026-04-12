# LLM Wiki — Schema

You are maintaining a personal knowledge base (wiki) by reading raw sources and building structured, interlinked markdown pages. Follow these conventions precisely.

## Directory Structure

```
raw/            # Immutable source documents. NEVER modify these.
wiki/           # AI-compiled knowledge base. You own this layer.
trusted/        # Human-curated verified content. NEVER modify these.
```

## Page Format

Every wiki page MUST have YAML frontmatter:

```yaml
---
title: "Page Title"
type: entity | concept | source | analysis
tags: [tag1, tag2]
sources: ["[[sources/source-name]]"]
created: 2026-04-12
updated: 2026-04-12
---
```

- First paragraph after frontmatter is always a one-sentence summary.
- Use Obsidian-style `[[wikilinks]]` for all cross-references.
- Use relative paths within wiki/: `[[entities/some-entity]]`, `[[concepts/some-concept]]`.

## Page Types

| Type | Location | Purpose |
|------|----------|---------|
| **Entity** | `wiki/entities/` | People, organizations, tools, products |
| **Concept** | `wiki/concepts/` | Ideas, themes, patterns, methodologies |
| **Source** | `wiki/sources/` | One summary per ingested source document |
| **Analysis** | `wiki/analysis/` | Filed query results, comparisons, syntheses |

## Operations

### Ingest

When told to ingest a source:

1. Read the source document in `raw/` completely.
2. Discuss key takeaways with the user (unless told to batch-ingest silently).
3. Create `wiki/sources/<source-name>.md` with a structured summary.
4. For each significant entity mentioned, create or update its page in `wiki/entities/`.
5. For each significant concept, create or update its page in `wiki/concepts/`.
6. Update `wiki/index.md` with new/changed pages.
7. Append an entry to `wiki/log.md`.
8. After all file changes, remind the user to git commit.

**Cross-referencing rules:**
- When updating an existing page with new information, clearly mark what's new: `*[Added from [[sources/source-name]]]*`
- When new information contradicts existing content, flag it: `> ⚠️ **Contradiction**: [old claim] vs. [new claim]. See [[sources/source-name]].`
- Add `[[wikilinks]]` to connect related pages.

### Query

When answering a question:

1. Read `wiki/index.md` to find relevant pages.
2. Read those pages to gather information.
3. Synthesize an answer with citations: `(see [[page-name]])`.
4. If the answer is substantive, offer to file it as `wiki/analysis/<topic>.md`.
5. Append the query to `wiki/log.md`.

### Lint

When asked to lint or health-check:

1. Scan all wiki pages for:
   - Orphan pages (not listed in index.md)
   - Broken `[[wikilinks]]` (target page doesn't exist)
   - Pages missing frontmatter or required fields
   - Index entries without corresponding files
2. LLM-driven checks:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Important concepts mentioned but lacking their own page
   - Missing cross-references between related pages
3. Report findings and offer to fix.
4. Append lint results to `wiki/log.md`.

## Rules

1. **NEVER modify files in `raw/` or `trusted/`.** These are human-owned.
2. **ALWAYS update index.md** when creating or significantly updating a wiki page.
3. **ALWAYS append to log.md** after any operation (ingest, query, lint).
4. **Use wikilinks** for all cross-references. Never use raw file paths in page content.
5. **Flag contradictions** explicitly. Do not silently overwrite conflicting information.
6. **Keep pages focused.** One entity per entity page, one concept per concept page.
7. **Preserve existing content** when updating. Add to pages; don't rewrite from scratch unless asked.

## Log Format

Each log entry follows this format for parseability:

```markdown
## [YYYY-MM-DD] operation | Title

Brief description of what was done.

Pages touched: [[page1]], [[page2]], [[page3]]
```

Operations: `ingest`, `query`, `lint`, `update`, `create`.
