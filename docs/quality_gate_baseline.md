# Quality Gate Baseline

This baseline documents the staged CI hardening path for the repository. It keeps the current diff reviewable and avoids mixing broad formatting or typing migrations into security-gate changes.

## Active gates

- Ruff is blocking for `E9`, `F63`, `F7`, `F82`, and `F541`.
- Black remains scoped to the existing helper-module allowlist until a dedicated format-only PR normalizes that baseline.
- mypy and Pyright cover the existing helper baseline plus clean Salary and ESCO core modules.
- Bandit is blocking for Medium/High findings after triage of current non-security SHA1 identifiers and XML parsing.
- Gitleaks is blocking in CI; repository hygiene still guards tracked local secret/artifact paths.
- Dependency Review blocks pull requests that introduce moderate-or-higher vulnerable dependencies.
- pip-audit runs as a blocking dependency vulnerability scan.
- Tracked artifact drift is blocking in CI and reports only paths and reasons.
- CodeQL runs in a dedicated workflow for Python with `security-and-quality` queries.
- Unit tests publish JUnit and coverage XML, with a minimum coverage threshold of 35%.
- Playwright captures advisory screenshots for central wizard screens.
- Deployed smoke runs against `CS_DEPLOYED_BASE_URL` when the repository variable is configured; otherwise the test is skipped by pytest.

## Deferred baseline expansions

- Ruff `F401` currently reports a large unused-import backlog, including re-export and Summary split-module leftovers. Add it only after triage or per-file baseline reduction.
- Black reports formatting changes inside the current allowlist. Expand the include only after a format-only PR.
- `llm_client.py` and `state.py` are not yet clean for mypy/Pyright. Current blockers are mostly Streamlit `SessionStateProxy` mutability/type compatibility and a small number of request/message typing issues.
- Full visual regression should move from screenshot artifacts to pixel baseline assertions once the team accepts stable reference screenshots and update rules.
