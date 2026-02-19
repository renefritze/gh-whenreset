# gh-whenreset

A GitHub CLI extension that prints local reset times for matching rate-limit buckets.
Repository: https://github.com/renefritze/gh-whenreset

## Behavior

- Input source:
  - If stdin is piped, reads `gh api /rate_limit` JSON from stdin.
  - If stdin is interactive, runs `gh api /rate_limit` automatically.
- Default filter: only not-full buckets are considered (`remaining < limit`).
- `--all`: consider all buckets instead.
- `--tz IANA_NAME`: override output timezone (for example `UTC` or `America/New_York`).

Output format (one line per matching bucket, sorted by reset time):

- `<local-time>  <bucket-name>  <relative-time>`
- `<local-time>` is `HH:MM` by default, and becomes `YYYY-MM-DD HH:MM` only when reset time is on a later local day.
- Example relative time: `in 10min`
- If a bucket is not exceeded (`remaining > 0`) and has a valid `limit`, the relative field includes `(<percent>% remaining)`.

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
