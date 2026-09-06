# Setup Guide

Get DronaAI.fit running on a fresh machine. Should take about 15 minutes.

Commands are written for **Windows PowerShell**. macOS/Linux equivalents are noted where they differ.

---

## 1. Install the tools

| Tool | Version | Notes |
|---|---|---|
| [Git](https://git-scm.com/downloads) | any | To clone the repo |
| [Python](https://www.python.org/downloads/) | 3.11+ | Tick **"Add python.exe to PATH"** in the installer |
| [Node.js](https://nodejs.org/) | 20 LTS+ | Use the **Windows Installer (.msi)** |

> **No admin rights?** The Python and Node installers both offer a per-user install that writes to your profile instead of `Program Files`. Don't tick "Install for all users".

Open a **new** terminal (so PATH updates apply) and check:

```powershell
git --version
python --version    # 3.11 or higher
node --version      # v20 or higher
```

> If `python --version` shows an older version, you have more than one Python installed. Use `py -3.11` in place of `python` throughout this guide.

### Install `uv` (Python package manager)

`uv` installs dependencies far faster than pip and can manage Python versions for you.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal, then verify:

```powershell
uv --version
```

Add it to your PATH permanently if the command isn't found:

```powershell
[Environment]::SetEnvironmentVariable("Path", "$env:USERPROFILE\.local\bin;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")
```

> **Prefer plain pip?** Skip `uv` and substitute `python -m venv .venv` and `pip install -r requirements.txt` in step 4.

---

## 2. Clone the repository

```powershell
git clone <repository-url>
cd "Fitness Assistant"
```

---

## 3. Set up the database

You need a PostgreSQL 16+ database. Pick whichever suits you.

### Option A — Supabase (recommended, no install)

Free, hosted, reachable from anywhere.

1. Sign up at [supabase.com](https://supabase.com) and click **New project**.
2. Set a **database password** and save it somewhere safe — it isn't shown again in plain text.
3. Under **Security**, disable **Data API** (this app connects straight to Postgres and doesn't use it).
4. Wait for provisioning to finish.
5. Go to **Project Settings → Database → Connection string → URI**.
6. Switch the mode dropdown to **Session pooler** and copy that URI.

> **Important:** use the **Session pooler** string, not "Direct connection". The direct hostname (`db.<ref>.supabase.co`) is IPv6-only and won't resolve on most networks. The pooler host looks like `aws-0-<region>.pooler.supabase.com` and the username includes your project ref: `postgres.<project-ref>`.

### Option B — Local PostgreSQL

1. Install [PostgreSQL 16](https://www.postgresql.org/download/windows/).
2. Create the database and user:

   ```powershell
   $env:PGPASSWORD = "<your postgres superuser password>"
   psql -U postgres -c "CREATE USER fitness WITH PASSWORD 'change_me';"
   psql -U postgres -c "CREATE DATABASE fitness OWNER fitness;"
   ```

   Your host is then `localhost:5432`, database `fitness`, user `fitness`.

---

## 4. Set up the backend

```powershell
cd backend

# Create the virtual environment (uv downloads Python 3.11 if you don't have it)
uv venv --python 3.11

# Activate it
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

> If PowerShell blocks the activation script, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Configure the environment

```powershell
Copy-Item .env.example .env
```

Open `backend/.env` and fill in your values:

```ini
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<database>
DATABASE_URL_SYNC=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
JWT_SECRET_KEY=<a long random string>
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:5174
FRONTEND_URL=http://localhost:5173
```

Leave `SMTP_HOST` empty for local development — verification and password reset emails are
printed to the backend console instead of being sent.

Both URLs point at the same database — the app uses the async driver, Alembic uses the sync one. Only the `postgresql+asyncpg` / `postgresql+psycopg` prefix differs.

**Using Supabase?** Take the URI you copied and swap the `postgresql://` prefix for each driver. For example:

```ini
DATABASE_URL=postgresql+asyncpg://postgres.abcdefgh:MyPassword@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
DATABASE_URL_SYNC=postgresql+psycopg://postgres.abcdefgh:MyPassword@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

> **Special characters in your password must be URL-encoded**, or the connection string won't parse:
> `@` → `%40` · `#` → `%23` · `%` → `%25` · `/` → `%2F` · `:` → `%3A`

Generate a JWT secret:

```powershell
-join ((1..48) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
```

### Create the tables and load demo data

```powershell
alembic upgrade head
python -m scripts.seed
```

You should see the seeded coaches and customers listed, ending with the shared demo password.

### Start the API

```powershell
uvicorn app.main:app --reload --reload-dir app
```

Open http://localhost:8000/docs — you should see the interactive API documentation.

> Leave this terminal running.

---

## 5. Set up the frontend

Open a **second** terminal:

```powershell
cd frontend

npm install

Copy-Item .env.example .env

npm run dev
```

Open http://localhost:5173 and log in with any [demo account](README.md#demo-accounts) — for example `coach.maria@example.com` / `Password123!`.

---

## 6. Verify it works

| Check | Expected |
|---|---|
| http://localhost:8000/docs | Swagger UI listing all endpoints |
| http://localhost:8000/api/v1/health | `{"status":"ok"}` |
| http://localhost:8000/api/v1/ready | `{"status":"ready"}` — confirms the database is reachable |
| http://localhost:5173 | Landing page with logo and Log in / Sign up |
| Log in as `coach.maria@example.com` | Customer dashboard showing 3 customers |
| Log in as `lena@example.com` | Diet plan waiting for approval; approve it to reveal the weekly plan |

---

## Signing up a new account locally

New accounts must verify their email before they can log in. Without SMTP configured, the
verification link is printed in the **backend terminal** — copy it into your browser to finish
signing up. The same applies to password reset links.

---

## Troubleshooting

### `getaddrinfo ENOTFOUND proxy.<company>.com`

A stale proxy environment variable. Clear it for the session and retry:

```powershell
$env:HTTP_PROXY = $null
$env:HTTPS_PROXY = $null
```

For npm specifically, also clear any saved config:

```powershell
npm config delete proxy
npm config delete https-proxy
```

### `socket.gaierror: [Errno 11001] getaddrinfo failed`

The Supabase hostname didn't resolve. You're most likely using the **Direct connection** string, which is IPv6-only. Switch to the **Session pooler** string (see step 3).

### `asyncpg.exceptions.InvalidPasswordError`

Wrong password, or a special character that wasn't URL-encoded. Re-check the encoding table in step 4, or reset the password in **Supabase → Project Settings → Database**.

### `CORS policy: No 'Access-Control-Allow-Origin' header`

Vite started on a different port than the backend allows. Check which port Vite printed, add it to `BACKEND_CORS_ORIGINS` in `backend/.env`, and restart the backend.

### `Port 5173 is in use, trying another one...`

An earlier dev server is still running. Either use the port Vite picked, or stop the old process:

```powershell
Get-NetTCPConnection -LocalPort 5173 -State Listen | Select-Object OwningProcess
Stop-Process -Id <the process id>
```

### `error while attempting to bind on address ('127.0.0.1', 8000)`

A backend is already running. Use it, or stop it the same way as above with port `8000`.

### `uvicorn: The term 'uvicorn' is not recognized`

The virtual environment isn't activated. Run `.\.venv\Scripts\Activate.ps1`, or call it directly with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

### Constant reloading / `CancelledError` spam in the backend

The file watcher is picking up changes from a cloud-sync folder (OneDrive, Dropbox). Scope the watcher to the app code:

```powershell
uvicorn app.main:app --reload --reload-dir app
```

### Logged in but getting 401s everywhere

Your stored token was signed with a different `JWT_SECRET_KEY`, or the demo data was reseeded. Log out and back in.

---

## Starting a fresh database

To wipe everything and start over:

```powershell
cd backend
python -m scripts.reset_data    # delete all rows
python -m scripts.seed          # reload demo data
```

To rebuild the schema from scratch as well:

```powershell
alembic downgrade base
alembic upgrade head
python -m scripts.seed
```

---

# Deploying

Frontend on Vercel, backend on Render, database on Supabase. All three have free tiers.

## 1. Set up email

Verification and password reset links are emailed. **Without SMTP configured, nobody can complete
sign-up** — the links only appear in the server log. Set this up before going live.

### Option A — Gmail (free, no domain needed, good for MVP)

1. Enable [2-Step Verification](https://myaccount.google.com/security) on the Google account
   you'll send from.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and
   create an app password.
3. Configure:

   ```ini
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.address@gmail.com
   SMTP_PASSWORD=<16-character app password, no spaces>
   SMTP_FROM=DronaAI.fit <your.address@gmail.com>
   ```

   Gmail forces the `From` address to match the authenticated account, so `SMTP_FROM` must use
   the same address as `SMTP_USER`.

   **Limits:** ~500 emails/day on a free Gmail account. Fine for an MVP or private beta; switch
   to a transactional provider before a public launch.

### Option B — Resend (needs a verified domain, scales further)

[Resend](https://resend.com) is free for 3,000 emails/month:

1. Sign up and verify a sending domain (or use their shared test address, which only delivers to
   your own Resend account email — fine for testing, not for real users).
2. Create an API key.
3. Configure:

   ```ini
   SMTP_HOST=smtp.resend.com
   SMTP_PORT=587
   SMTP_USER=resend
   SMTP_PASSWORD=<your API key>
   SMTP_FROM=DronaAI.fit <no-reply@yourdomain.com>
   ```

Any SMTP provider works the same way — Mailgun, SendGrid, Postmark, etc.

## 2. Lock down the database

By default the app connects as the Postgres **superuser**. Create a restricted role instead, so a
compromised app can't drop tables:

```powershell
cd backend
python -m scripts.create_app_role
```

It prints a connection string. Use it for `DATABASE_URL` and keep `DATABASE_URL_SYNC` pointing at
the owner account — Alembic needs schema rights to run migrations.

## 3. Deploy the backend to Render

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repo. It reads [`render.yaml`](render.yaml).
3. Set these environment variables in the Render dashboard (the file deliberately leaves them
   blank so secrets never land in git):

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Supabase pooler URL with the `fitness_app` role |
   | `DATABASE_URL_SYNC` | Same host, owner account, `postgresql+psycopg://` prefix |
   | `BACKEND_CORS_ORIGINS` | Your Vercel URL, e.g. `https://fitness.vercel.app` |
   | `FRONTEND_URL` | The same Vercel URL |
   | `SMTP_*` | From step 1 |

   `JWT_SECRET_KEY` is generated automatically. `ENVIRONMENT`, `COOKIE_SECURE` and
   `COOKIE_SAMESITE` are already set correctly in the blueprint.

Migrations run automatically before each deploy via `preDeployCommand`.

## 4. Deploy the frontend to Vercel

1. **New Project**, select the repo, set the root directory to `frontend`.
2. Vercel reads [`frontend/vercel.json`](frontend/vercel.json) for the build and SPA routing.
3. Add one environment variable:

   ```ini
   VITE_API_BASE_URL=https://your-api.onrender.com
   ```

4. Deploy, then go back to Render and set `BACKEND_CORS_ORIGINS` and `FRONTEND_URL` to the real
   Vercel URL.

## 5. Seed the first coach

Coaches can self-register, but you may want to create the first one yourself. From your machine,
with `.env` pointing at the production database:

```powershell
cd backend
python -m scripts.seed
```

Remove or edit [`scripts/seed.py`](backend/scripts/seed.py) first if you don't want the demo
accounts in production — they all share a published password.

## Why cookie settings matter

The frontend and API sit on different domains, so the session cookie must be cross-site:

| Setting | Local | Deployed |
|---|---|---|
| `COOKIE_SECURE` | `false` | `true` |
| `COOKIE_SAMESITE` | `lax` | `none` |

With `SameSite=lax` across domains the browser silently drops the cookie and **login appears to
succeed but every subsequent request is unauthenticated**. The blueprint sets these correctly.

## Post-deploy checklist

| Check | Expected |
|---|---|
| `https://your-api.onrender.com/docs` | **404** — docs are disabled in production |
| `https://your-api.onrender.com/api/v1/ready` | `{"status":"ready"}` |
| Sign up with a real email | Verification email arrives |
| Log in, refresh the page | Still logged in |
| 11 rapid failed logins | The 11th returns `429` |

> Render's free tier sleeps after 15 minutes of inactivity, so the first request after a pause
> takes ~30 seconds. Upgrade to a paid instance if that matters.
