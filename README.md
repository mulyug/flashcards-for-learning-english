# Flashcards

A single-user web app for learning English vocabulary with spaced repetition
(SM-2). FastAPI + Jinja + HTMX + SQLite, packaged with Docker and fronted by
Caddy for automatic HTTPS via Let's Encrypt (DNS challenge through Cloudflare).

## Features

- Create / edit / delete cards: English, translation, optional example
- Spaced repetition (SM-2): rate each card as Hard / Medium / Easy and the
  next review date is computed automatically
- Single-user authentication: only you can manage your deck
- Brute-force protection: per-IP rate limit on `/login` plus per-account
  lockout after repeated failures
- Argon2 password hashing, HttpOnly + Secure signed-session cookies,
  double-submit-cookie CSRF, strict security headers, automatic HTTPS

## Stack

| Layer    | Choice                                |
| -------- | ------------------------------------- |
| API      | FastAPI 0.115+ on Uvicorn             |
| UI       | Jinja2 + HTMX + Tailwind play CDN     |
| DB       | SQLite + SQLAlchemy 2 + Alembic       |
| Auth     | Argon2 + signed cookie (itsdangerous) |
| Limits   | slowapi (in-memory)                   |
| HTTPS    | Caddy 2 + Cloudflare DNS challenge    |
| Runtime  | Docker + docker-compose               |

## Project layout

```
app/                 FastAPI application
  main.py            Entry point, middleware, route mounting
  config.py          Settings (env-driven)
  db.py              SQLAlchemy engine and session
  models.py          User, Card models
  security.py        Argon2 + signed-session helpers
  csrf.py            Double-submit CSRF middleware + dependency
  rate_limit.py      slowapi limiter + 429 handler
  srs.py             Pure SM-2 algorithm
  deps.py            DB session, current-user dependencies
  render.py          Template render helper
  templating.py      Jinja2Templates instance
  routers/           auth, cards, review
  templates/         Jinja2 templates
alembic/             Migrations
scripts/
  create_user.py     CLI to create the single owner account
caddy/Caddyfile      Reverse proxy + HTTPS via Cloudflare DNS challenge
caddy/Dockerfile     Caddy build with cloudflare-dns plugin
Dockerfile
docker-compose.yml
tests/test_srs.py    Unit tests for SM-2
```

## Local development (without HTTPS)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest pytest-asyncio httpx

# .env for local
cat > .env <<EOF
SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
DATABASE_URL=sqlite:///./data/dev.db
COOKIE_SECURE=false
DOMAIN=localhost
EOF

mkdir -p data
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.create_user
.venv/bin/uvicorn app.main:app --reload
```

Open <http://localhost:8000> and sign in.

Run tests:

```bash
.venv/bin/python -m pytest -v
```

## Deploy with Docker (production)

### Prerequisites

- A domain with DNS managed by **Cloudflare** (free plan is enough)
- DNS A record pointing to your server's IP
- A Cloudflare API token with **Edit zone DNS** permission for your domain

### Steps

1. Add your domain to Cloudflare and point its A record at the server IP.
   Set **Proxy status** to **DNS only** (grey cloud).

2. Create a Cloudflare API token:
   - **My Profile → API Tokens → Create Token**
   - Use the **Edit zone DNS** template
   - Set **Zone Resources** → your domain
   - Copy the token (shown only once)

3. On the server, clone the repo and create `.env`:

   ```bash
   cat > .env <<EOF
   SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
   DATABASE_URL=sqlite:////data/app.db
   COOKIE_SECURE=true
   DOMAIN=your-domain.com
   CLOUDFLARE_API_TOKEN=your_cloudflare_token
   EOF
   ```

4. Open port **8443** in your firewall:

   ```bash
   ufw allow 8443
   ```

5. Create the data directory and build:

   ```bash
   mkdir -p data
   docker compose up -d --build
   ```

   Caddy obtains a Let's Encrypt certificate via Cloudflare DNS challenge on
   first boot (no ports 80/443 needed). Logs: `docker compose logs -f caddy`.

6. Create the single user (one-time):

   ```bash
   docker compose run --rm app python -m scripts.create_user
   ```

7. Visit `https://your-domain.com:8443` and sign in.

### Backup

The entire database is one file: `./data/app.db`. Back it up with `cp` or
`rsync` while the app is stopped (or use `sqlite3 .backup` for hot copies).

## Security notes

- **Rate limit:** `/login` accepts at most `LOGIN_MAX_ATTEMPTS` requests per
  `LOGIN_LOCKOUT_MINUTES` per source IP (defaults: 5 / 15 min). Excess
  requests get HTTP 429.
- **Account lockout:** independent of rate limit, after
  `LOGIN_MAX_ATTEMPTS` invalid passwords against an existing account, the
  account itself is locked for `LOGIN_LOCKOUT_MINUTES` — even with the
  correct password.
- **CSRF:** every unsafe request must carry a token matching the
  `csrf_token` cookie. HTMX-driven calls send it via the `X-CSRF-Token`
  header (auto-wired in `base.html`); plain forms include a hidden field.
- **Headers set on every response:** `Strict-Transport-Security` (Caddy),
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Permissions-Policy`, and a strict `Content-Security-Policy`.
- **Cookies:** session and CSRF cookies are `Secure` (with
  `COOKIE_SECURE=true`) + `SameSite=Lax`. Session cookie is `HttpOnly`.

## Environment variables

| Var                     | Default                  | Notes                              |
| ----------------------- | ------------------------ | ---------------------------------- |
| `SECRET_KEY`            | required                 | 32+ byte hex; signs session cookie |
| `DATABASE_URL`          | `sqlite:////data/app.db` | SQLAlchemy URL                     |
| `DOMAIN`                | `localhost`              | Used by Caddy for cert issuance    |
| `CLOUDFLARE_API_TOKEN`  | required in production   | API token with Edit zone DNS       |
| `COOKIE_SECURE`         | `true`                   | `false` only for local HTTP dev    |
| `SESSION_MAX_AGE_DAYS`  | `7`                      |                                    |
| `LOGIN_MAX_ATTEMPTS`    | `5`                      |                                    |
| `LOGIN_LOCKOUT_MINUTES` | `15`                     |                                    |

## SM-2 details

`Hard`, `Medium`, `Easy` map to SuperMemo quality scores `2`, `3`, `5`.
Quality `< 3` resets the repetition counter and reschedules the card for
tomorrow. Ease factor is updated by the standard SM-2 formula and floored at
`1.3` so intervals can recover. See `app/srs.py` and `tests/test_srs.py`.
