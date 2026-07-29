import asyncio
import httpx

class HttpClientPool:
    _client: httpx.AsyncClient = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        # Fast path: already constructed — no lock needed
        if cls._client is None or cls._client.is_closed:
            async with cls._lock:
                # Double-check after acquiring lock (another coroutine may
                # have finished construction while we were waiting)
                if cls._client is None or cls._client.is_closed:
                    cls._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
