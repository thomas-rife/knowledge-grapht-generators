# Deploying the questions service on Vercel

The service is one Python function (`api/index.py`) with no third-party
dependencies. Every path is rewritten to it by `vercel.json`. It stores nothing.

## 1. Put the folder in Git

This folder isn't a Git repository yet. Create a private repository for it and
push. `.gitignore` should exclude `__pycache__/` and `preview/`.

## 2. Create the Vercel project

Import the repository in Vercel as a new project. Framework preset: **Other**.
No build command or output directory is needed.

## 3. Environment variables (Production and Preview)

| Variable | Value |
| --- | --- |
| `GENERATORS_SECRET` | 32+ random characters. Signs question tokens; changing it invalidates open questions. |
| `GENERATORS_API_KEY` | A different random string. Apps send it as `X-Generators-Key`. |
| `GENERATORS_ENABLE_CODE_RUNNER` | Leave unset. `1` publishes `python.write_function`, which runs student code without a sandbox: test environments only. |

Generate values with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## 4. Deployment Protection

The admin and Studio servers call this service directly, so Vercel's login
wall must not sit in front of it. Either turn Deployment Protection off for this
project's production domain (the API key still guards every request), or keep
it on and have the apps send Vercel's protection-bypass header.

## 5. Check it

```sh
curl -H "X-Generators-Key: $KEY" https://<project>.vercel.app/health
curl -H "X-Generators-Key: $KEY" https://<project>.vercel.app/generators
```

`/health` returns `{"ok": true}`; a missing or wrong key returns 401.

## 6. Point the apps at it

In both the admin app and Studio (Vercel environment variables, and
`.env.local` for local development):

```
GENERATORS_API_URL=https://<project>.vercel.app
GENERATORS_API_KEY=<the same key as above>
```

Never prefix these with `NEXT_PUBLIC_`: only the apps' servers may hold the key.

## Running locally instead

```sh
GENERATORS_SECRET=dev-secret-0123456789abcdef GENERATORS_API_KEY=dev-key \
  python3 -m generators.api --port 8787
```

and set `GENERATORS_API_URL=http://127.0.0.1:8787` in the apps.
