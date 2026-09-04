from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage — correct for this app, which intentionally runs as a
# single uvicorn process (the health/alert/retention background pollers are
# in-process asyncio tasks; running multiple worker processes would each run
# their own duplicate copy of them, so that's not how this scales). A shared
# store (e.g. Redis) would only be needed if that assumption ever changes.
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
