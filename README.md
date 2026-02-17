# gh-whenreset

A GitHub CLI extension that reads `gh api /rate_limit` JSON from stdin and prints the latest local reset time among matching rate-limit buckets.

## Behavior

- Default: only exhausted buckets are considered (`remaining == 0`).
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

From GitHub (after publishing this repo as `gh-whenreset`):

```bash
gh extension install <OWNER>/gh-whenreset
```

## Usage

Default (only exhausted buckets):

```bash
gh api /rate_limit | gh whenreset
```

Consider all buckets:

```bash
gh api /rate_limit | gh whenreset --all
```

Force timezone:

```bash
gh api /rate_limit | gh whenreset --tz UTC
```
