# Guestbook Backend

A tiny Flask API that powers the guestbook on my portfolio's [Contact page](https://0l-l.github.io/contact.html). Visitors can leave a short public message; the messages are stored server-side and shown back to everyone who visits the page.

Built for CMU 15-113, HW4 (Backend + Frontend).

## What it does

Three endpoints:

| Method | Path                | Body / Headers                              | What it does |
|--------|---------------------|----------------------------------------------|--------------|
| GET    | `/messages`          | none                                          | Returns all guestbook messages as JSON, most recent first. |
| POST   | `/messages`          | JSON `{ "name": "...", "message": "..." }`    | Validates and stores a new message. Returns the created entry with a generated `id` and `created_at` timestamp, or a `400` with an `error` field if validation fails (missing name/message, or over the length limit). |
| DELETE | `/messages/<id>`     | Header `X-Admin-Token: <token>`               | Deletes a message by id. Requires the correct admin token (moderation-only, not exposed on the public site) — returns `401` if missing/wrong, `503` if no token is configured on the server at all. |

`GET /` is a plain health check (`{"status": "ok"}`) used to confirm the service is awake.

Messages are stored in a local `messages.json` file on the server rather than a full database, since this is a small, low-stakes dataset and it avoids extra infra. Note this means data can reset if the Render service redeploys or restarts — a known, acceptable tradeoff for this assignment (a real database would be a natural next step for Project 2).

## How the frontend communicates with it

The frontend (on GitHub Pages, in the separate `0l-l.github.io` repo) is a form on `contact.html`. On load, it calls `GET /messages` and renders the list. On submit, it calls `POST /messages` with the visitor's name and message, then re-fetches the list to show the new entry. If the request fails (backend asleep, network error, validation error), the page shows an inline error message instead of crashing or hanging silently.

## Running it locally

```bash
pip install -r requirements.txt
python3 app.py
```

This starts the server at `http://127.0.0.1:5000`. Test it with curl:

```bash
curl http://127.0.0.1:5000/messages
curl -X POST http://127.0.0.1:5000/messages \
  -H "Content-Type: application/json" \
  -d '{"name":"Oulan","message":"Hello!"}'
```

To test the moderation `DELETE` endpoint locally, set `ADMIN_TOKEN` before starting the server (see `.env.example`):

```bash
ADMIN_TOKEN=some-random-string python3 app.py
```

## Environment variables / secrets

- `ADMIN_TOKEN` — a secret string that authorizes deleting a message. Set it as an environment variable on Render (dashboard → Environment), never committed to the repo. `.env` is git-ignored; `.env.example` shows the shape without a real value. If `ADMIN_TOKEN` isn't set, `DELETE` is disabled entirely (returns `503`) rather than silently allowing unauthenticated deletes.
- No other secrets are used — `GET`/`POST /messages` are intentionally public since a guestbook is meant to be public.

## Deploying

Deployed as a Render Web Service:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Environment variable:** `ADMIN_TOKEN` set to a random string in the Render dashboard.

## Tech

Python + Flask, no database, no external API calls. CORS is handled manually (see `app.py`) rather than via `flask-cors`, so there's one less dependency that can fail to install.
