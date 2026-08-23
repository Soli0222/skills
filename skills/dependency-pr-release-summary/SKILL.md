---
name: dependency-pr-release-summary
description: Summarize open dependency update pull requests with repo diffs, chart/package changes, rendered impact, and upstream application release impact. Use when a user asks to inspect open Renovate/dependency PRs, especially Helm/Flux chart updates, and wants to know not only what version changed in the repo but what application release(s) those updates imply.
---

# Dependency PR Release Summary

## Goal

Produce a one-pass, review-ready summary of dependency PRs. Do not stop at the PR diff or Helm chart release notes: determine whether the deployed application itself changes, and summarize the upstream application release impact when it does.

## Workflow

1. Resolve the repository from local git context, then list open PRs:
   - `git remote -v`
   - `gh pr list --state open --limit 100 --json number,title,author,headRefName,baseRefName,labels,url,statusCheckRollup,updatedAt`
2. For every open PR, collect structured context:
   - `gh pr view <num> --json number,title,body,files,commits,headRefName,baseRefName,url,statusCheckRollup`
   - `gh pr diff <num>`
   - `gh pr view <num> --comments --json comments` when CI posts rendered diffs or summary comments.
3. Extract the repo-level change:
   - package/chart/action name
   - old and new version
   - changed files
   - affected cluster(s), inferred from paths such as `flux/clusters/<cluster>/...`, `helmfile/...`, `ansible/...`, or `.github/workflows/...`
4. Determine whether this is a Helm/chart wrapper update, app binary update, GitHub Action update, Ansible var update, or another dependency type.
5. For Helm/Flux chart updates, resolve the chart metadata at both old and new chart versions:
   - Prefer `Chart.yaml` from the chart source repo when tags and paths are obvious.
   - Use `helm show chart <repo/chart-or-oci> --version <version>` for OCI charts or when the chart source layout is not available.
   - Compare `version` and `appVersion`.
6. If `appVersion` changed, fetch and summarize the upstream application release(s), not just the chart release:
   - Use official GitHub releases or changelogs for the application source.
   - For a version range, include all relevant app releases between old and new.
   - Group details into security/hardening, features, behavior/API changes, bug fixes, compatibility, and operational impact when applicable.
7. If `appVersion` did not change, say clearly: "アプリ本体 release 差分なし". Then summarize only chart-level effects such as sidecar/config-reloader images, default value changes, templates, CRDs, RBAC, PVC retention, or generated manifest differences.
8. For non-Helm dependencies:
   - GitHub Actions: summarize action release notes and clarify it is not runtime app impact.
   - Ansible/binary vars: fetch the upstream application release and compare notes, then explain operational rollout impact.
   - CRD-only charts: distinguish app/operator release notes from actual CRD/rendered changes in this repo.
9. Inspect repo manifests for application-specific usage before giving impact statements. Examples:
   - CNPG: search for `Cluster`, `ScheduledBackup`, `Backup`, `DatabaseRole`, `Pooler`, `barman`, `imageName`.
   - Flux: inspect `FluxInstance`, component list, version constraints, old API versions.
   - Loki/Prometheus/Grafana: inspect rendered diff comments and values if chart defaults changed.

## Output

Return a compact but information-rich table. Include these columns unless the user asks for a different format:

- `PR`
- `PKE 側の変更`
- `chart / package`
- `アプリ本体`
- `アプリ本体の差分`
- `PKE での注意点`

Use links for PRs and upstream releases. Split the table or add short sections if a single table becomes too wide, but keep the app release impact visible in the main answer.

## Quality Bar

- Do not present chart release notes as application release notes.
- Do not imply the app changed when `appVersion` is unchanged.
- Do not omit upstream app release details for updates where `appVersion`, binary version, or operator version changed.
- Call out when rendered diff coverage is incomplete, such as a workflow that only diffs one cluster while a PR affects another.
- Prefer primary sources: PR metadata, PR diff, official chart metadata, official release notes/changelogs, and repo manifests.
- When a fact could have changed, verify it live with `gh`, official release pages, or the repository contents.
