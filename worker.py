import os
import redis
from rq import Worker, Queue, Connection
from core.config import Config

# Listen to these queues
listen = ['high', 'default']

# Use the REDIS_URL from our central config
redis_url = getattr(Config, 'REDIS_URL', 'redis://localhost:6379/0')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        print("--- Starting RQ Worker ---")
        print(f"Connected to: {redis_url}")
        print(f"Queues: {listen}")
        worker.work()
