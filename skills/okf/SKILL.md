---
name: okf
description: Author, update, review, validate, and consume Open Knowledge Format (OKF) knowledge bundles. Use when working with OKF, markdown files with YAML frontmatter for knowledge catalogs, data catalogs, metadata-as-code, agent-readable documentation, bundle indexes, concept documents, citations, cross-links, or OKF conformance for Claude or Codex skills.
---

# Open Knowledge Format

## Overview

Use this skill to work with Open Knowledge Format (OKF): a vendor-neutral knowledge-bundle format made of markdown concept documents with YAML frontmatter.
The same `SKILL.md` instructions are intended to be usable by Claude and Codex; Codex-specific UI metadata may live under `agents/`.

## Core Rules

Create and preserve OKF as plain UTF-8 markdown files in a directory tree.
Treat each non-reserved `.md` file as one concept document.
Use these reserved filenames only for their defined purposes:

- `index.md`: directory listing for progressive disclosure.
- `log.md`: chronological update history.

Every concept document must start with YAML frontmatter:

```markdown
---
type: <Type name>
title: <Optional display name>
description: <Optional one-line summary>
resource: <Optional canonical URI>
tags: [<tag>, <tag>]
timestamp: <ISO 8601 datetime>
---
```

Require only `type`.
Prefer also writing `title`, `description`, `resource`, `tags`, and `timestamp` when known.
Preserve unknown frontmatter keys when editing existing OKF documents.

Use standard markdown for the body.
Prefer structural sections such as `# Schema`, `# Examples`, and `# Citations` when applicable.
Use markdown links to express relationships between concepts:

- Bundle-relative links such as `/tables/orders.md` are preferred.
- Relative links such as `./orders.md` are allowed.
- Broken links should be reported but not treated as fatal.

## Authoring Workflow

When creating or expanding an OKF bundle:

1. Identify the bundle root and target audience.
2. Inventory concepts before writing files.
3. Choose a simple hierarchy that supports discovery, such as `datasets/`, `tables/`, `metrics/`, `apis/`, `playbooks/`, or `references/`.
4. Write one markdown concept document per stable knowledge unit.
5. Add cross-links in prose wherever concepts relate to each other.
6. Add citations for external claims under `# Citations`.
7. Add or update `index.md` files so readers can traverse the bundle one directory at a time.
8. Add or update `log.md` only when the user wants change history.
9. Validate the bundle before finalizing.

For concept documents, copy `assets/concept.md` as a starting point when useful.
For directory indexes, copy `assets/index.md`.
For update logs, copy `assets/log.md`.

## Editing Workflow

When modifying an existing bundle:

1. Read the local `index.md` first if it exists, then open the specific concept files needed.
2. Preserve the user's directory layout, naming conventions, title style, and existing frontmatter extensions.
3. Avoid rewriting unrelated concepts.
4. Keep concept IDs stable unless the user explicitly asks to reorganize files.
5. If moving or renaming a concept, update inbound and outbound links when practical.
6. Keep citations attached to the claims they support.
7. Regenerate only the relevant `index.md` files after content changes.

## Consuming Workflow

When using an OKF bundle as context:

1. Start at the bundle root `index.md` if present.
2. Traverse progressively through subdirectory `index.md` files.
3. Open only the concept documents needed for the task.
4. Use frontmatter for filtering and routing.
5. Use the markdown body for semantics, examples, schema details, citations, and relationships.
6. Treat links as directed relationship edges whose meaning comes from surrounding prose.
7. Tolerate unknown `type` values, unknown frontmatter keys, missing optional fields, broken links, and missing indexes.

## Validation

Run the bundled validator before delivering a bundle or after substantial edits:

```bash
python3 scripts/validate_okf.py <bundle-root>
```

The validator checks:

- concept files have frontmatter.
- concept frontmatter has non-empty `type`.
- `index.md` entries use markdown links.
- `log.md` date headings use `YYYY-MM-DD`.
- bundle-relative and relative links are checked as warnings.

If `PyYAML` is installed, the validator uses it for YAML parsing.
Without `PyYAML`, it performs a conservative built-in check that is sufficient for common OKF frontmatter.

## Reference

Read `references/spec.md` when the user asks specification-level questions, when conformance details matter, or when a document uses edge cases not covered above.
