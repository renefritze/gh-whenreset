# gh-whenreset

A GitHub CLI extension that prints the latest local reset time among matching rate-limit buckets.
Repository: https://github.com/renefritze/gh-whenreset

## Behavior

- Input source:
  - If stdin is piped, reads `gh api /rate_limit` JSON from stdin.
  - If stdin is interactive, runs `gh api /rate_limit` automatically.
- Default filter: only exhausted buckets are considered (`remaining == 0`).
- `--all`: consider all buckets instead.
- `--tz IANA_NAME`: override output timezone (for example `UTC` or `America/New_York`).

Output format:

- `<local-iso8601-timestamp>\t<bucket-name>\t<relative-time>`
- Example relative time: `in 10min`

If no buckets match the chosen criteria, the command exits with status `2` and prints a clear message to stderr.

## Install

From a local clone:

```bash
gh extension install .
```

From GitHub:

```bash
gh extension install renefritze/gh-whenreset
```

## Usage

Default (auto-fetch from GitHub API):

```bash
gh whenreset
```

Consider all buckets:

```bash
gh whenreset --all
```

Force timezone:

```bash
gh whenreset --tz UTC
```

Use pre-fetched JSON from stdin:

```bash
gh api /rate_limit | gh whenreset
```
