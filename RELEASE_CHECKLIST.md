# Release Checklist

- `pytest -q`
- `slidebridge version`
- `slidebridge env`
- `slidebridge readers`
- create-demo smoke test
- render-overlay smoke test
- build wheel/sdist
- `twine check`
- fresh wheel install
- sensitive content scan
- `git status` clean
- tag release

