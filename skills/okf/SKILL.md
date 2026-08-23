---
name: okf
description: Author, update, review, validate, and consume Open Knowledge Format (OKF) knowledge bundles. Use when working with OKF, markdown files with YAML frontmatter for knowledge catalogs, data catalogs, metadata-as-code, agent-readable documentation, bundle indexes, concept documents, provenance and trust frontmatter, attested computations, cross-links, or OKF conformance for Claude or Codex skills.
---

# Open Knowledge Format

## Overview

Use this skill to work with Open Knowledge Format (OKF): a vendor-neutral knowledge-bundle format made of markdown concept documents with YAML frontmatter.
This skill targets **OKF v0.2**, which adds first-class provenance, trust, lifecycle, and attestation on top of v0.1's plain markdown-plus-frontmatter.
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
---
```

Require only `type`; a concept carrying just `type` is conformant.
Prefer also writing `title`, `description`, `resource`, and `tags` when known.
Add the provenance, trust, and lifecycle fields below whenever the information exists.
Preserve unknown frontmatter keys when editing existing OKF documents.

Write every timestamp as an ISO 8601 datetime with an explicit UTC offset, such as `2026-08-23T14:00:00Z`.

Use standard markdown for the body.
Prefer structural sections such as `# Schema`, `# Examples`, and `# Computation` when applicable.
Use markdown links to express relationships between concepts:

- Bundle-relative links such as `/tables/orders.md` are preferred.
- Relative links such as `./orders.md` are allowed.
- Broken links should be reported but not treated as fatal.

## Provenance, Trust, and Lifecycle

These frontmatter families are optional, but their absence carries meaning, so write them whenever the information is available.

```yaml
sources:
  - id: ga4-schema
    resource: https://developers.google.com/analytics/bigquery/export-schema
    title: GA4 BigQuery Export schema
    author: team:ga4-docs
    usage_count: 5000
    last_modified: 2026-05-30T00:00:00Z
usage_window: { from: 2026-06-01T00:00:00Z, to: 2026-06-30T00:00:00Z }
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-20T22:53:05Z }
verified:
  - { by: human:ahormati, at: 2026-06-25T09:00:00Z }
status: stable
stale_after: 2026-09-23T00:00:00Z
```

- `sources`: the materials the concept derives from. Each entry requires `resource`, which is either a followable artifact (URL, bundle-relative path, `references/` path) or a scope descriptor such as `all queries in BigQuery project X`. Give an entry an `id` whenever the body cites it.
- Credibility signals `author`, `usage_count`, and `last_modified` are per-source facts, not a score. Never write a credibility score; record the signals and let consumers infer. `usage_count` needs a `usage_window` to be meaningful; write `usage_window` once as a sibling of `sources`, or per entry to override. `author` nominally follows the actor convention below, but the spec's own example deviates; see the note under Validation.
- `generated`: how the current content was produced. `by` is required and is an actor; `at` marks the last meaningful content change.
- `verified`: who or what has confirmed the content, as a list of `{ by, at }` events. A bare mapping is legal and means a one-element list. Keep it distinct from `generated`: writing and confirming are different acts.
- `status`: `draft`, `stable`, or `deprecated`. Absent means `stable`.
- `stale_after`: the absolute instant at which the content goes stale. Not a relative TTL.

Write actors with one of three shapes:

- `<producer>/<version>` for agents and tools, such as `reference_agent/gemini-2.5-pro`.
- `human:<id>` for a person.
- `process:<id>` for an automated process.

Use the `human:` prefix for anything hand-authored or human-confirmed; consumers derive trust tiers from it (no `verified` means unverified, non-human verifiers mean machine-confirmed, a `human:` verifier means human-reviewed).

Attribute individual claims with markdown footnotes whose label is a `sources[].id`:

```markdown
The `events_` table is sharded daily as `events_YYYYMMDD`.[^ga4-schema]

[^ga4-schema]: GA4 BigQuery Export schema
```

The label is the join key into `sources`, so keep ids stable across rewrites.

## Attested Computations

When a concept carries a sanctioned way to compute a value, make the computation its own concept with `type: Attested Computation` and link to it from the concepts that use the value.
Give each figure its own computation concept rather than packing several into one frontmatter, since `verified`, `stale_after`, and `attester` describe exactly one thing.

```yaml
type: Attested Computation
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: references/attesters/revenue.py
```

- `runtime` is required for this type and determines what `parameters` mean.
- Supply the computation either inline as a single fenced block under `# Computation`, or as a `computation:` path with no body fence. Do not do both.
- `executor.resource` names run instructions or code; `executor.receipt` lists the evidence fields a run must return.
- `attester.resource` names deterministic, no-LLM code that inspects a receipt and returns a verdict.

When acting as the agent that uses a computation, supply values only for the declared `parameters`.
Never author or edit the computation itself, and never substitute an improvised query.

Keep `verified` and attestation distinct: `verified` confirms the definition still matches policy and lives in the bundle; attestation confirms one run produced the value the sanctioned way and is a runtime artifact that is never stored in the bundle.

## Authoring Workflow

When creating or expanding an OKF bundle:

1. Identify the bundle root and target audience.
2. Inventory concepts before writing files.
3. Choose a simple hierarchy that supports discovery, such as `datasets/`, `tables/`, `metrics/`, `apis/`, `playbooks/`, `computations/`, or `references/`.
4. Write one markdown concept document per stable knowledge unit.
5. Record `sources` for the material each concept was derived from, and attach footnote attributions to the specific claims they support.
6. Record `generated` on everything written, using the actor convention.
7. Add `status` and `stale_after` where lifecycle matters, and `verified` once something has actually confirmed the content.
8. Add cross-links in prose wherever concepts relate to each other.
9. Add or update `index.md` files so readers can traverse the bundle one directory at a time.
10. Add or update `log.md` only when the user wants change history.
11. Declare `okf_version: "0.2"` in the bundle-root `index.md` frontmatter, the only place frontmatter is permitted in an `index.md`.
12. Validate the bundle before finalizing.

For concept documents, copy `assets/concept.md` as a starting point when useful.
For attested computations, copy `assets/computation.md`.
Both carry `REPLACE-WITH-` placeholders in `generated`; fill them with the actor that actually wrote the document.
Never leave `human:` provenance on something an agent generated.
For directory indexes, copy `assets/index.md`.
For update logs, copy `assets/log.md`.

## Editing Workflow

When modifying an existing bundle:

1. Read the local `index.md` first if it exists, then open the specific concept files needed.
2. Preserve the user's directory layout, naming conventions, title style, and existing frontmatter extensions.
3. Avoid rewriting unrelated concepts.
4. Keep concept IDs stable unless the user explicitly asks to reorganize files.
5. Keep `sources[].id` values stable; footnote attribution joins on them, so renaming one silently misattributes claims.
6. Update `generated` when content meaningfully changes. Do not touch `verified` — only an actual verification event adds an entry there.
7. If moving or renaming a concept, update inbound and outbound links when practical.
8. Regenerate only the relevant `index.md` files after content changes.

When a bundle is still on v0.1, migrate rather than mixing conventions:

- `timestamp` becomes `generated: { by, at }`, with `at` carrying the old value.
- A body `# Citations` list becomes `sources` entries, with per-claim footnotes replacing the numbered references.

Migrate a document only when otherwise editing it, or when the user asks for a bundle-wide migration.

## Consuming Workflow

When using an OKF bundle as context:

1. Start at the bundle root `index.md` if present.
2. Traverse progressively through subdirectory `index.md` files.
3. Open only the concept documents needed for the task.
4. Use frontmatter for filtering and routing.
5. Weigh `verified`, `sources` credibility signals, `status`, and `stale_after` before relying on a claim, and say so when relying on something unverified, deprecated, or past its `stale_after`.
6. Use the markdown body for semantics, examples, schema details, and relationships.
7. Treat links as directed relationship edges whose meaning comes from surrounding prose.
8. For an Attested Computation, load the contract, supply parameter values only, run it through the declared executor, and check the receipt with the declared attester. Surface a failing attestation instead of dropping it.
9. Tolerate unknown `type` values, unknown frontmatter keys, missing optional fields, broken links, and missing indexes.
10. Fall back to a legacy `timestamp` when `generated` is absent, and to a legacy `# Citations` list when `sources` is absent.

## Validation

The validator needs PyYAML, since conformance rests on the frontmatter being parseable YAML.
Install it first if the check fails with exit code 2:

```bash
python3 -m pip install pyyaml
```

Run the validator before delivering a bundle or after substantial edits:

```bash
python3 scripts/validate_okf.py <bundle-root>
```

It reports two levels, and they are not interchangeable:

- **ERROR** is a conformance failure under spec §11: a concept without parseable YAML frontmatter, a missing or empty `type`, or an `index.md` or `log.md` that breaks the structure in §8 and §9. Only these decide whether a bundle is conformant.
- **WARN** is everything else. The spec states the rest as SHOULD, so a bundle may knowingly ignore a warning and remain conformant. A malformed optional family lands here too, because §11 forbids rejecting a concept over one.

Warnings still matter. Read them, and fix them unless the deviation is deliberate.
The lint covers:

- `generated`, `verified`, `sources`, `usage_window`, `tags`, `status`, and `stale_after` being well-formed, with actors matching the convention and timestamps carrying a UTC offset.
- footnote labels used in a body resolving to a `sources[].id`.
- `type: Attested Computation` concepts declaring `runtime` and providing exactly one computation, plus well-formed `parameters`, `executor`, and `attester`.
- `index.md` entries using markdown links, and root index frontmatter carrying only `okf_version`.
- path-valued fields and cross-links resolving.
- v0.1 leftovers: a `timestamp` with no `generated`, and a body `# Citations` list.

Two flags adjust what fails the run:

- `--conformance` runs only the §11 checks and skips the lint. Use it to answer "is this a conformant bundle" without the quality opinions.
- `--strict` makes warnings fail the run. Use it on bundles this skill authored, where every warning should have been resolved.

The validator does not check `sources[].author` against the actor convention.
Spec §5.1 says it follows the convention, but the spec's own example writes `team:ga4-docs`, which §7 does not define.
Treat this as a known upstream ambiguity: write `author` in the actor convention when the producer fits one of the three shapes, and do not treat a team-style value as an error.

Regression tests for the validator live in `tests/run.sh` at the repository root, under the `okf` filter:

```bash
./tests/run.sh okf
```

## Reference

Read `references/spec.md` when the user asks specification-level questions, when conformance details matter, or when a document uses edge cases not covered above.
It is a verbatim copy of the OKF v0.2 specification from [GoogleCloudPlatform/open-knowledge-format](https://github.com/GoogleCloudPlatform/open-knowledge-format) (`SPEC.md` at `0b87c52`, Apache-2.0).
The earlier copy under `GoogleCloudPlatform/knowledge-catalog/okf` is a frozen snapshot and is no longer the canonical source.
