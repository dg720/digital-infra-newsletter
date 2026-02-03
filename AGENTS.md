# AGENTS.md - Generic Codex Project Operating Guide

This is a **project-agnostic** operating guide for a Codex-style coding agent with terminal + git access.
Follow this guide unless `SPEC.md` (or explicit project instructions) override it.

## 1) Sources of truth (precedence)

1. `RAILWAY_CLI_DEPLOY.md` / `DEPLOY*.md` -- deployment steps, environment variables, service layout.
2. `SPEC.md` -- requirements, user flows, pages, API contracts, and acceptance criteria.
3. `README.md` -- local setup/run/test commands and repo conventions.
4. Code + tests -- if docs conflict, rely on tests and observed runtime behavior.

## 2) Working style

- Make small, verifiable changes.
- Prefer simple implementations over clever ones.
- Keep progress visible (checklists in PR notes or `NOTES.md` if helpful).
- For UI/UX changes, feature debugging, and end-to-end verification, use the Playwright MCP to drive the browser and validate flows.

## 3) Execution loop (build -> test -> deploy)

Repeat until the stop condition is met:

1. Read the relevant `SPEC.md` section.
2. Plan the smallest change set.
3. Implement.
4. Run local checks (lint/format if present) and tests.
5. Run a smoke test (key routes/endpoints) locally.
6. Debug until green.
7. For UI/UX or end-to-end changes, run Playwright MCP review cycles to validate behavior and fix issues. Cap at 3 cycles; if still failing, stop and report findings and next steps.
8. Commit with a clear message.
9. Deploy using `RAILWAY_CLI_DEPLOY.md` step-by-step.
10. Run live smoke tests against the deployed URL.

## 4) Debugging protocol

When something fails:

- Reproduce deterministically (command + inputs + expected vs actual).
- Inspect logs (local + Railway).
- Minimise scope (smallest failing component).
- Fix root cause (avoid band-aids).
- Add/extend a test to prevent regression.
- Re-run local suite and live smoke tests.
- For UI/UX issues, reproduce and validate fixes using the Playwright MCP.

## 5) Documentation rules

- Keep `README.md` accurate: setup, run, test, and env vars.
- Document non-obvious choices in `DECISIONS.md` (optional).
- Keep this file (`AGENTS.md`) generic; project-specific behavior belongs in `SPEC.md`.

## 6) Quality gates (minimum)

Before marking a feature "done":

- Matches `SPEC.md` acceptance criteria.
- No obvious UI console errors (frontend projects).
- API endpoints return expected JSON shapes and status codes.
- A minimal automated smoke test exists (script, curl, or test file) covering:
  - backend health check
  - one core end-to-end user flow
- Build is reproducible from a clean checkout.

## 7) Git hygiene

- Use a branch per task: `feat/...`, `fix/...`.
- Commit frequently with clear messages: `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`.
- Never commit secrets.

## 8) Deployment discipline (Railway)

- Follow `RAILWAY_CLI_DEPLOY.md` exactly.
- Confirm required env vars exist.
- After deploy: load the frontend, call critical API endpoints, and check logs.
- If deploy fails: fix, redeploy, and re-verify.

## 9) Security defaults

- Validate inputs at API boundaries.
- Avoid logging sensitive data.
- Set safe upload limits and file type allowlists.
- Rate-limit abuse-prone endpoints.

## 10) Stop condition

Stop only when:

- All acceptance criteria in `SPEC.md` are satisfied.
- Local tests pass.
- Deployment is live and smoke tests pass against the deployed app.
- Docs are updated enough for another developer to run and deploy.
