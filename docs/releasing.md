# Releasing harness-orchestrator

## Overview

Releases are automated via GitHub Actions. Pushing a version tag triggers the full CI pipeline, builds the wheel, and publishes to PyPI.

## Release Steps

1. **Bump version** in `pyproject.toml`:

   ```bash
   # Edit pyproject.toml: version = "X.Y.Z"
   ```

2. **Commit and tag**:

   ```bash
   git add pyproject.toml
   git commit -m "chore: release vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

3. **Automated pipeline** (runs on tag push):

   ```
   v* tag pushed
     → CI: lint + test (Python 3.9-3.13) + build
     → Verify tag version == pyproject.toml version
     → Publish to PyPI (trusted publishing / OIDC)
     → Create GitHub Release with auto-generated notes
   ```

4. **Verify**: Check [PyPI](https://pypi.org/project/harness-orchestrator/) and [GitHub Releases](https://github.com/arthaszeng/harness-orchestrator/releases).

## Version Scheme

- **PATCH** (2.1.0 → 2.1.1): bug fixes, docs, minor improvements
- **MINOR** (2.1.x → 2.2.0): new features, backward-compatible changes
- **MAJOR** (2.x.x → 3.0.0): breaking changes (ask user before bumping)

## PyPI Setup (one-time)

1. Create account at [pypi.org](https://pypi.org)
2. Register the project name `harness-orchestrator`
3. Configure [trusted publisher](https://pypi.org/manage/project/harness-orchestrator/settings/publishing/):
   - Owner: `arthaszeng`
   - Repository: `harness-orchestrator`
   - Workflow: `release.yml`
   - Environment: `pypi`
4. In GitHub repo settings, create an environment named `pypi`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Tag version mismatch | Ensure `pyproject.toml` version matches the tag (without `v` prefix) |
| CI fails on tag push | Fix the issue, delete the tag, re-tag after fix |
| PyPI auth error | Verify trusted publisher config matches workflow file |
| Package name conflict | `harness-orchestrator` is the registered name on PyPI |
