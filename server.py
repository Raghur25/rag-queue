from dotenv import load_dotenv
load_dotenv()

from client.rq_client import queue
from fastapi import FastAPI, HTTPException, Query

# Job is referenced by import path so the API never imports queues/worker.py.
# That module connects to the model server and Qdrant at import time, which
# only the RQ worker process should do.
PROCESS_QUERY_JOB = "queues.worker.process_query"

app = FastAPI()

@app.get("/")
def root():
    return {"message": "server is up and running"}

@app.post('/chat')
def chat(
    query: str = Query(..., description="The chat query from the user")   
):
    job = queue.enqueue(PROCESS_QUERY_JOB, query)
    
    return { "status": "queued", "job_id": job.id }

@app.get('/job_status')
def get_result(
    job_id: str = Query(..., description="The job ID")
):
    job = queue.fetch_job(job_id=job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found (unknown id or expired)")

    status = job.get_status().value  # plain string: queued / started / finished / failed ...

    return {
        "job_id": job.id,
        "status": status,
        "result": job.result if status == "finished" else None,
        "error": job.exc_info.strip().splitlines()[-1] if status == "failed" and job.exc_info else None,
    }