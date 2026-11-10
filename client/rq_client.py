from redis import Redis
from rq import Queue

# Valkey is published on host port 6380 (6379 is taken by another project's Redis)
queue = Queue(connection=Redis(
    host="localhost",
    port=6380
))
