# Security audit — ShapeEvoluty / ProgressoFit (Django 6.1 + allauth)

Scope: all project code (apps `contas`, `metricas`, `nutricao`, `treinos`, `core`), settings, templates, JS, dependencies, `.env`, database and media files.
Verification: 56 automated tests (16 original + 40 new security tests), `manage.py check --deploy`, `pip-audit`, `bandit`, and migrations applied to a copy of your real `db.sqlite3`.

## 1. Fixed

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Uploads served openly at `/media/`** (professional ID documents, proof photos, progress photos reachable by anyone who knew/guessed the URL; in production not served at all) | `/media/...` now goes through `core.views.media_protegida`: login required + per-folder permission (documents: owner/staff only; progress photos: owner/staff; ranking proofs: owner/staff or verified+public; avatars: logged users). Only files referenced in the DB are served; path traversal blocked; images inline, everything else as download; `CSP: sandbox` + `nosniff` on every file. URLs did not change, so templates/admin keep working. |
| 2 | **Unsafe uploads**: `documento_verificacao` accepted any file type/size (an `.mp4` is already in your media folder); images had no size/format limit | Real content check (Pillow / `%PDF-` signature), extension must match content, JPG/PNG/WEBP/PDF only, 5 MB images / 8 MB documents, pixel cap (decompression bomb). SVG/HTML/EXE rejected. Files saved with random UUID names (no original names/dates leaked). Legacy files are not revalidated (they keep working). |
| 3 | **Insecure production config**: no secure cookies, HSTS, HTTPS redirect; weak `SECRET_KEY` not rejected; no `STATIC_ROOT` | `settings.py`: when `DEBUG=False` → secure session/CSRF cookies, HTTPS redirect, HSTS (30 days to start), `SECRET_KEY` checked (refuses `django-insecure-*`/short keys), `CSRF_TRUSTED_ORIGINS`, proxy header option, upload/body size limits, SameSite/HttpOnly/nosniff/frame-deny/referrer policy, logging to console. `check --deploy` is clean except two optional HSTS items (subdomains/preload). |
| 4 | **Brute force / abuse**: Django admin login bypasses allauth's limits; no limits on expensive/spammable actions | Admin login: 10 attempts/min/IP (429). allauth limits tightened (login 5/min/IP + 5 per 5 min per account, signup, reset). New per-user limits on AI generation (8/h), ranking submissions (5/h, max 10 pending), photos, metrics, forms. |
| 5 | **Duplicate submissions / AI cost abuse**: double click or F5 created duplicate records; `GET /treinos/` re-called the paid Gemini API on every refresh when a plan was missing | Server-side lock (one in-flight POST per user per action; stays locked briefly after a successful submit; released immediately on validation errors) + client script `static/js/envio-unico.js` disables the submit button (also added to the allauth pages). GET regeneration limited to 3/h with its own lock. |
| 6 | **Sensitive error leakage**: provider error text (key/project/model hints, "check GEMINI_MODEL in .env") shown to users | Users get generic messages; details only in server logs. |
| 7 | **Missing input validation** (server + HTML attrs): negative/absurd measures, unlimited text sent to the AI | Ranges on all metrics/ranking values, `tempo_minutos` 10–300, length caps on all free-text fields (also reduces prompt-stuffing), ranking category whitelisted, reserved usernames (`privacidade` shadowed a route; `admin`/`suporte` impersonation). |
| 8 | **Private profile leaked real name and bio** to any logged-in user | Hidden unless owner or profile is public. Viewing someone else's profile no longer writes a `Perfil` row. |
| 9 | **AI output trusted blindly** (stored as-is) and prompt injection via form fields | Output structure validated and size-capped before saving; system prompt now says user fields are data, not instructions. Output is rendered with Django auto-escaping (no XSS). Model name validated before going in the URL; redirects disabled; request timeout split. |
| 10 | **Vulnerable dependency**: `urllib3 2.7.0` (3 known advisories) | Bumped to `2.8.0`; `pip-audit` now reports none. |
| 11 | **Third-party script without integrity** (Chart.js from cdnjs) | Chart.js 4.4.0 now self-hosted from the official npm package (`metricas/static/metricas/js/vendor/`). |
| 12 | Weak password policy / long reset window | Minimum length 10; reset link valid 1 h (was 3 days). |
| 13 | Functional bug found on the way: `redirect('treinos:home')` (URL doesn't exist) → 500 after generating a plan | → `treinos:treino`. |
| 14 | `env-example` out of sync (`ANTHROPIC_API_KEY` vs code using Gemini); `.gitignore` gaps | Rewritten with all variables; ignores `.env*`, `*.sqlite3`, `/media/`. |

## 2. Checked and OK (not just "exists")
- **SQL injection**: ORM only; no `raw()/extra()/cursor()` anywhere. Bandit: 0 real findings (2 false positives).
- **CSRF**: middleware on; every POST form has `{% csrf_token %}`; the privacy toggle sends `X-CSRFToken`; tested that POSTs without a token get 403. Logout is POST.
- **IDOR**: every query is filtered by `request.user`; profile privacy enforced server-side; privacy toggle POST-only and only touches own profile; users cannot self-set `profissional_verificado` (tested).
- **Passwords**: PBKDF2-SHA256 in the DB (all 3 users); no custom password storage.
- **Account enumeration**: allauth `PREVENT_ENUMERATION` on. Email verification mandatory.
- **XSS**: autoescape everywhere; no `|safe`/`mark_safe`/`innerHTML`; chart data via `json_script`.
- **CORS**: no CORS package/headers → same-origin only (secure default). **SSRF**: only outbound call is to a fixed Google host; no user-controlled URL.
- **Clickjacking**: `X-Frame-Options: DENY`. **Open redirect**: allauth validates `next`.
- **Secrets in Git**: `.env`, `db.sqlite3`, `media/` were never committed in this repo's history (2 commits). (`CORRECOES.md` says otherwise — it is not true for this copy.)

## 3. Remaining risks
- **No Content-Security-Policy**: templates use inline scripts/styles (and Google Fonts), so an enforcing CSP would break the UI. Needs a small refactor (nonces / move inline JS out).
- **Rate limits live in process memory** (LocMemCache). With several gunicorn workers/servers limits are per worker — use Redis/DatabaseCache.
- **SQLite** in production: fine for a demo/academic app, not for concurrent load. Use PostgreSQL if this grows.
- **Django serves the media files** (OK for small scale). At scale, serve through Nginx `internal` + `X-Accel-Redirect` keeping the same permission view.
- **Photo EXIF/GPS not stripped** from uploaded images.
- **Public usernames**: allauth auto-generates usernames at signup (they appear derived from the email); they are shown on profile/ranking URLs. Check what yours look like, and consider asking for a display name at signup.
- Private profiles still show username, avatar, level and photo count to logged users (this was your explicit design).
- Admin has no 2FA; staff can see all private uploads.
- `perfil.html` still contains hard-coded demo content (fake nutritionist "Dra. Camila Nogueira — CRN 12345", fixed "32 treinos"): remove before real users see it.
- Gemini cost abuse is limited per user, but accounts are free: consider a daily global cap/budget alert in Google Cloud.

## 4. Manual actions (cannot be done in code)
1. **Rotate credentials**: the `.env` I received contains a Gmail app password, a Gemini API key and the Django `SECRET_KEY`. Treat them as exposed: revoke/regenerate all three. Never share the project zip with `.env`/`db.sqlite3`/`media/`.
2. In production `.env`: `DEBUG=False`, new `SECRET_KEY`, real `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS=https://yourdomain`, a custom `ADMIN_URL` (e.g. `painel-x7k2/`), and if behind a proxy `TRUST_PROXY_SSL_HEADER=True` (only if the proxy overwrites `X-Forwarded-Proto`). Raise `HSTS_SECONDS` to 31536000 once HTTPS is stable.
3. Serve **only** `/static/` from the web server (`collectstatic`); never expose the `media/` folder directly; set `client_max_body_size 10m` in Nginx.
4. Run `python manage.py migrate` (3 small migrations: upload naming only, no data change) and `python manage.py test`.
5. Create/verify the admin's e-mail, use a unique strong admin password, and review `RegistroRanking` / documents only through the admin.
6. Existing files in `media/` keep their old names (e.g. `IMG_2023...jpg`, one `.mp4` document). Delete/replace what you don't need; new uploads get random names.
7. Re-run `pip-audit -r requirements.txt` before each deploy.
