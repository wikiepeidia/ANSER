import redis
import sys
import os

# Add parent directory to sys.path to import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config

def check_redis():
    redis_url = getattr(Config, 'REDIS_URL', 'redis://localhost:6379/0')
    print(f"Checking Redis connection to: {redis_url}")
    
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis connection successful!")
        return True
    except redis.exceptions.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("Ensure Redis is running and the URL is correct.")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    if check_redis():
        sys.exit(0)
    else:
        sys.exit(1)
