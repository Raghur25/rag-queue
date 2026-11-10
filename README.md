# rag-queue

A small service that answers questions over a Qdrant RAG index **without blocking the web API**.
The API puts each question on a queue and returns a job id right away. A separate worker does the slow
part (vector search + LLM call), and you poll for the result.

```
POST /chat?query=...        FastAPI ──enqueue──►  Valkey (queue)  ◄──take job──  RQ worker
   └─► {"job_id": "..."}                                                           │ 1. embed question, search Qdrant
GET /job_status?job_id=...  FastAPI ◄──read status/result── Valkey ◄──save answer──┘ 2. ask the LLM with the retrieved chunks
```

| Part | Where |
|---|---|
| API (`/`, `/chat`, `/job_status`) | `main.py` (starts uvicorn), `server.py` (routes) |
| Queue connection | `client/rq_client.py` |
| Job function run by the worker | `queues/worker.py` → `process_query` |
| Valkey (Redis-compatible queue store) | `docker-compose.yml` (host port **6380**) |

## Prerequisites

- Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker
- A Qdrant instance on `localhost:6333` that already contains a collection named `learning_rag`
  (create it with [naive-rag](https://github.com/Raghur25/naive-rag))
- An OpenAI-compatible server exposing an embedding model named `embedding` and a chat model named `qwen3`
  (change the names in `queues/worker.py` if yours differ)

## Run it

```bash
uv sync
cp .env.example .env                  # fill in OPENAI_BASE_URL and OPENAI_API_KEY
docker compose up -d                  # Valkey on localhost:6380
```

Start the API (terminal 1) and the worker (terminal 2), both from this folder:

```bash
uv run python main.py                 # API on http://127.0.0.1:8000  (Swagger UI at /docs)
```

```bash
# Linux / macOS
uv run rq worker --url redis://localhost:6380

# Windows (no os.fork, so use the in-process worker)
uv run rq worker --worker-class rq.SimpleWorker --url redis://localhost:6380
```

Then in Swagger (`/docs`): call `POST /chat` with a `query`, copy the `job_id`, and call
`GET /job_status` until `status` is `finished`.

## Job states

`queued` → `started` → `finished` (answer in `result`) or `failed` (last line of the error in `error`).
Finished results are kept for 500 seconds (RQ default), after which `/job_status` returns 404.

## Notes

- Valkey is published on **6380** so it does not clash with a Redis already running on 6379.
- Start the worker from this folder: RQ finds `queues.worker.process_query` through the current directory.
- `queues/worker.py` connects to Qdrant and the model server the first time a job runs, so a down server shows up as a `failed` job.
- `OpenAIEmbeddings(check_embedding_ctx_length=False)` is required for non-OpenAI embedding models (see the naive-rag README).
