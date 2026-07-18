import os
import redis
from dotenv import load_dotenv

# Đảm bảo worker đọc HF_BASE_URL + config DB từ .env
load_dotenv()

from rq import Queue
from core.config import Config

# Listen to these queues
listen = ['high', 'default']

# Use the REDIS_URL from our central config
redis_url = getattr(Config, 'REDIS_URL', 'redis://localhost:6379/0')
conn = redis.from_url(redis_url)

# Windows KHÔNG có os.fork() -> SimpleWorker (xử lý job ngay trong process).
# Linux/Colab -> Worker thường (fork, nhanh hơn).
if os.name == 'nt':
    from rq import SimpleWorker as WorkerClass
else:
    from rq import Worker as WorkerClass

if __name__ == '__main__':
    # RQ 2.x: bỏ 'with Connection(...)', truyền connection= thẳng vào Queue & Worker
    queues = [Queue(name, connection=conn) for name in listen]
    worker = WorkerClass(queues, connection=conn)

    print("--- Starting RQ Worker ---")
    print(f"Connected to: {redis_url}")
    print(f"Queues: {listen}")
    print(f"Worker class: {WorkerClass.__name__}")
    worker.work()