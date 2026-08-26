# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Teaching material for a 2-hour workshop ("Kubernetes & Agents IA", CNCG Lomé) aimed at
an audience with **zero prior knowledge** of both Kubernetes and AI agents. Audience-facing
material and the slide plan are in **French**; code, manifests and READMEs are in English.

Current state: **specification only, no code yet.**

- `prompt.md` — the full build spec for the demo application (`agent-app/`). This is the
  source of truth for the implementation.
- `plan-slides.md` — 18-slide plan + 3 labs with a minute-by-minute time budget. This is
  the source of truth for *why* the app is shaped the way it is.

Read both before writing any code. Many "obviously wrong" choices in the spec are
deliberate teaching devices, described below.

## Architecture to build (`agent-app/`)

FastAPI service, one HTTP hop in front of an LLM:

```
HTTP client → agent-app (FastAPI) → LiteLLM gateway → (unknown upstream provider)
```

Layering, one concern per module:
- `app/main.py` — app factory + router registration only. No business logic.
- `app/config.py` — `pydantic-settings` `BaseSettings`; all LLM config from env.
  `LLM_BASE_URL` and `LLM_API_KEY` are **required with no default** — never give
  `llm_base_url` a fallback value. The same image has to target the online workshop
  gateway or a local LiteLLM by environment alone (`host.docker.internal` from a
  container, `host.k3d.internal` from a Pod).
- `app/services/llm.py` — the only module that talks to the gateway, via plain `httpx`
  (not the `openai` SDK — the raw request shape must stay readable on a slide).
- `app/routers/{chat,stats,health}.py` — one router per endpoint.
- `app/state.py` — the in-memory counter.

A single `httpx.AsyncClient` is created in the FastAPI lifespan handler and handed to the
chat router by dependency injection — not one client per request.

Endpoints: `POST /chat` → `{reply, served_by}`, `GET /stats` → `{total_requests, served_by}`,
`GET /health` → `{status: "ok"}`.

## Invariants — do not "improve" these

Each maps to a moment in the workshop. Changing one breaks a lab.

1. **The request counter is a plain in-memory int** in `app/state.py`, reset on process
   start. No Redis, no DB, no persistence. Lab 3 has participants scale to 5 replicas and
   watch the counters diverge — that divergence *is* the lesson (slide 14).
2. **`served_by` is `socket.gethostname()`** — the pod name under Kubernetes. Repeated
   calls make load balancing visible (Lab 3, step 2).
3. **`/health` stays trivial** — no upstream call, no logic. It backs the liveness probe
   that slide 11 uses to answer "Docker doesn't detect a stuck process".
4. **`/stats` and `/health` must work with the gateway down or the key invalid.** Only
   `/chat` may fail. This is the workshop's network plan B: Labs 2 and 3 must still run
   if LiteLLM is unreachable in the room.
5. **No provider name anywhere in the code** — the string "deepseek" must not appear. The
   app knows only the gateway.
6. **`LLM_API_KEY` never appears** in the image, a committed file, a log line, or an error
   response. Missing key → fail fast at startup with a clear message. Upstream failure →
   HTTP 502 with a short JSON message.
7. **No logging setup, no tests, no CI beyond the build/push workflow, no auth, no DB.**
   Observability is explicitly out of scope for this workshop.

## Kubernetes manifests (`k8s/`)

Target is **k3d** (single node, on a laptop). Participants apply manifests straight from
raw GitHub URLs — so they must work **unedited**:

- `configmap.yaml` (`agent-config`) — `LLM_BASE_URL`, `LLM_MODEL` (non-sensitive, versioned).
- `deployment.yaml` (`agent-app`) — those two via `configMapKeyRef`; `LLM_API_KEY` via
  `secretKeyRef` on Secret `agent-secret`. Resource **requests are mandatory** (the HPA
  cannot compute CPU utilisation without them).
- `service.yaml` — **NodePort**, 80 → 8000, fixed `nodePort: 30080`. NodePort is a
  superset of ClusterIP, so everything still works (in-cluster DNS, `port-forward`) on a
  k3d cluster created without a port mapping — participants who created theirs with
  `-p "30080:30080@server:0"` additionally get `curl localhost:30080`. Never downgrade
  this to ClusterIP: `kubectl port-forward svc/...` pins a single Pod, which would make
  `served_by` constant and kill Lab 3, step 2.
- `pvc.yaml` — `agent-data`, RWO, 1Gi, storage class `local-path` (k3s default provisioner).
- `hpa.yaml` — 1→5 replicas, ~50% CPU. Applied last.

**The Secret is deliberately absent from the repo.** Each group creates it with their own
LiteLLM virtual key. The visible contrast between "what's in `k8s/` and what isn't" is the
whole of slide 16 — don't add a `secret.yaml`, even an example one.

Manifests are read line by line on screen by people who have never seen YAML. Keep them
plain and sparsely commented.

## Image & CI

Participants **never run `docker build`** — they pull a prebuilt public image from GHCR.
`.github/workflows/build-push.yml` builds **multi-arch (`linux/amd64` + `linux/arm64`)**;
the room is a mix of Intel and Apple Silicon and a single-arch image fails for half of it.
Auth via the built-in `GITHUB_TOKEN`, tags `:latest` + commit SHA, `type=gha` layer cache.

The Dockerfile must carry the `org.opencontainers.image.source` OCI label so the package
inherits the repo's permissions **before** first publish, install deps in a layer before
copying `app/`, and run as a non-root user.

## Local commands (once `agent-app/` exists)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload            # from agent-app/
docker run -p 8000:8000 -e LLM_BASE_URL=... -e LLM_API_KEY=sk-... -e LLM_MODEL=... \
  ghcr.io/denisakp/agent-app:latest
```

There is no test suite and none is wanted.

## Editing the slide plan

`plan-slides.md` is timed to the minute and already over-tight (2 min of slack for 2 h).
Adding a slide means removing one. Two documented shock absorbers exist: block 5
(slides 13–15) compresses from 8 min to 4, and step 5 of Lab 3 is optional. The one
continuity thread not to break: the three Docker gaps announced on slide 7 are answered,
in that same order, on slides 11–12.
