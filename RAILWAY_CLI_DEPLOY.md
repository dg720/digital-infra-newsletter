# Railway CLI Deploy Guide (Template)

Use this template for new projects. It assumes a two-service setup (backend + frontend).
Replace all placeholders in <> with your values. Use the repo name as the project name, and use `<repo-name>-frontend` and `<repo-name>-api` for frontend and backend service names.

## Prereqs
- Railway CLI installed and authenticated (`railway login`)
- Repo cloned locally
- Working directory is repo root

## 0) Safety: do not overwrite an existing project
- If this directory is already linked, unlink first:

```bash
railway unlink
```

- Create a NEW project:

```bash
railway init -n <repo-name> -w "Dhruv Gupta's Projects"
```

## 1) Link project and environment

```bash
railway link --project <project-id> --environment production --workspace "Dhruv Gupta's Projects"
```

## 2) Create services

```bash
railway add --service <repo-name>-api
railway add --service <repo-name>-frontend
```

## 3) Deploy backend

Deploy from the backend subdirectory (monorepo-safe):

```bash
railway service <repo-name>-api
railway up <backend-root> --path-as-root -s <repo-name>-api -d
```

Backend start command (example Procfile):

```
web: uvicorn <module>:<app> --host 0.0.0.0 --port $PORT
```

## 4) Add persistent storage (optional)

```bash
railway service <repo-name>-api
railway volume add -m /data
railway variables --set "ISSUES_DIR=/data/issues"
```

## 5) Set backend env vars

```bash
railway service <repo-name>-api
railway variables --set "CORS_ORIGINS=https://<your-frontend-domain>"
railway variables --set "OPENAI_API_KEY=sk-..."
```

Security note: do not store API keys or Railway tokens in this repo. Use environment variables.
Example: `railway login` or set `RAILWAY_TOKEN` in your shell/CI.

## 6) Deploy frontend

Deploy from the frontend subdirectory (monorepo-safe):

```bash
railway service <repo-name>-frontend
railway up <frontend-root> --path-as-root -s <repo-name>-frontend -d
```

## 7) Frontend env vars

Pick ONE package manager and keep it consistent. This template uses **npm**.

```bash
railway service <repo-name>-frontend
railway variables --set "NEXT_PUBLIC_API_URL=https://<your-backend-domain>"
railway variables --set "BACKEND_API_BASE_URL=https://<your-backend-domain>"
```

If needed:

```bash
railway variables --set "NODE_OPTIONS=--max-old-space-size=512"
```

## 8) Verify services

Backend:

```bash
curl https://<your-backend-domain>/api/health
```

Frontend:

```bash
open https://<your-frontend-domain>
```

## 9) Build prerequisites

Monorepo deploys must use `--path-as-root`.

If using npm, keep `package-lock.json` in sync:

```bash
cd <frontend-root>
npm install
```

Commit the updated lockfile before deploying.

## 10) Debugging and logs

Build logs (last 200 lines):

```bash
railway logs -s <repo-name>-frontend --build -n 200
```

Deploy/runtime logs:

```bash
railway logs -s <repo-name>-frontend -n 200
```

List deployments and inspect a specific one:

```bash
railway deployment list -s <repo-name>-frontend
railway logs --build <deployment-id>
railway logs <deployment-id>
```

## 11) Common fixes
- Wrong root folder: deploy from `<backend-root>` or `<frontend-root>`.
- Lockfile out of date: run `npm install` (or the package manager you chose).
- Frontend hangs: backend base URL must include `https://` and be reachable.
- Frontend build fails with `@/lib/*` not found: ensure `newsletter-generator-ui/lib` is not ignored by `.gitignore` (see note below).

---

## Current deployment (Feb 2, 2026)
- Project: `digital-infra-newsletter` (ID: `9236fd5e-e18e-4bf4-b170-a462c5efa827`) in workspace "Dhruv Gupta's Projects".
- Services: `digital-infra-newsletter-api`, `digital-infra-newsletter-frontend`.
- Volume: attached to `digital-infra-newsletter-api` at `/data`; env `ISSUES_DIR=/data/issues`.
- API domain: https://digital-infra-newsletter-api-production.up.railway.app (uvicorn via Procfile).
- Frontend domain: https://digital-infra-newsletter-frontend-production.up.railway.app
- Frontend build fixed by un-ignoring `newsletter-generator-ui/lib` (root `.gitignore` previously ignored all `lib/` dirs).
- Frontend envs set: `NEXT_PUBLIC_API_URL` + `BACKEND_API_BASE_URL` -> API domain, `NEXT_FORCE_WEBPACK=1`.
- API envs set: OpenAI/Tavily keys, model vars, `MAX_TOOL_CALLS_PER_AGENT=12`, `ISSUES_DIR=/data/issues`.
- Backend dependency fix: added `lxml_html_clean` to satisfy `newspaper3k` on Python 3.13.
