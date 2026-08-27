# Agent App

A minimal AI agent: it receives a message over HTTP, forwards it to an
OpenAI-compatible gateway, and returns the model's answer along
with the name of the instance that served it.

Workshop material for *Kubernetes & Agents IA* (CNCG Lomé).

## Endpoints

| Method | Path      | Response                                   |
|--------|-----------|--------------------------------------------|
| `POST` | `/chat`   | `{"reply": "...", "served_by": "..."}`      |
| `GET`  | `/stats`  | `{"total_requests": 3, "served_by": "..."}` |
| `GET`  | `/health` | `{"status": "ok"}`                          |

`served_by` is the container hostname — the Pod name on Kubernetes. The counter
behind `/stats` lives in memory, in that instance only: run several replicas and
each one counts on its own.

## Configuration

Everything comes from the environment. See `.env.example`.

| Variable        | Required | Description                                        |
|-----------------|----------|----------------------------------------------------|
| `LLM_BASE_URL`  | yes      | Gateway base URL, incl. `/v1`. Workshop: `https://r7umxvllm.denisakp.me/v1` |
| `LLM_API_KEY`   | yes      | Gateway virtual key (`sk-...`). Never commit it.    |
| `LLM_MODEL`     | no       | Model alias exposed by the gateway (`groq-120b`)    |

The application refuses to start if `LLM_BASE_URL` or `LLM_API_KEY` is missing.
No gateway URL is baked into the image or the code — it is always read from the
environment, so you can point the same image at any OpenAI-compatible gateway.

### Pointing at a local gateway

The hostname to use depends on where the *app* runs, not where the gateway runs:

| App runs in…            | `LLM_BASE_URL`                          |
|-------------------------|-----------------------------------------|
| `uvicorn` on the host   | `http://localhost:4000/v1`              |
| a Docker container      | `http://host.docker.internal:4000/v1`   |
| a Pod in k3d            | `http://host.k3d.internal:4000/v1`      |

`localhost` inside a container is the container itself, not your machine — that is the
usual reason a local gateway "doesn't answer". `host.k3d.internal` is injected by k3d
into the node containers and the CoreDNS ConfigMap, so it resolves from any Pod.

For k3d, override the ConfigMap value without editing the file:

```bash
kubectl set env deployment/agent-app LLM_BASE_URL=http://host.k3d.internal:4000/v1
kubectl rollout status deployment/agent-app
# back to the workshop gateway:
kubectl set env deployment/agent-app --from=configmap/agent-config
```

## Run the prebuilt image

No build needed — the image is public on GHCR:

```bash
docker run -p 8000:8000 \
  -e LLM_BASE_URL=https://r7umxvllm.denisakp.me/v1 \
  -e LLM_API_KEY=sk-your-virtual-key \
  -e LLM_MODEL=groq-120b \
  ghcr.io/denisakp/agent-app:latest
```

Then:

```bash
curl -s localhost:8000/health
curl -s localhost:8000/stats
curl -s localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message": "Bonjour !"}'
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your key
uvicorn app.main:app --reload
```

Interactive API docs: <http://localhost:8000/docs>

## Deploy on Kubernetes

The `k8s/` folder holds the manifests. Create the Secret first — it is not in the
repo, since it contains your key:

```bash
kubectl create secret generic agent-secret --from-literal=LLM_API_KEY=sk-your-virtual-key
kubectl apply -f k8s/
kubectl port-forward svc/agent-app 8000:80
```

`k8s/configmap.yaml` already points at the workshop gateway (`https://r7umxvllm.denisakp.me/v1`).
Edit `LLM_BASE_URL` there only if you run your own.

## Build the image yourself (optional)

Only if you want to modify the code — participants do not need this.

```bash
docker build -t agent-app:dev .
```

Pushes to `main` build and publish a multi-architecture image
(`linux/amd64` + `linux/arm64`) to GHCR via GitHub Actions.
