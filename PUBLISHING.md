# Publishing

This package is published to PyPI with Trusted Publishing from GitHub Actions.
No PyPI token is required in GitHub secrets.

## One-time PyPI setup

Create a PyPI account, then add a pending trusted publisher with these values:

| Field | Value |
|---|---|
| PyPI project name | `heroshots` |
| Owner | `JasonPriore` |
| Repository name | `HeroShotsSDK-Python` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

If PyPI asks for the project before the first upload, choose the pending
publisher flow. The first successful workflow run will create the project.

## Release process

1. Update `version` in `pyproject.toml`.
2. Run the local checks:

   ```bash
   python -m pip install -e ".[dev]"
   pytest -q
   python -m pip install --upgrade build twine
   python -m build
   python -m twine check dist/*
   ```

3. Commit the version change.
4. Create and push a matching tag:

   ```bash
   git tag v0.2.3
   git push origin main --tags
   ```

5. Create a GitHub Release from that tag.

The `Publish to PyPI` workflow runs on the published GitHub Release, verifies
that the tag matches `pyproject.toml`, builds the source distribution and wheel,
checks both artifacts, then publishes them to PyPI.

PyPI versions are immutable. If a version has already been uploaded, bump the
version and publish a new release instead of reusing the old version number.
