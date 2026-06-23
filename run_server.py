import sys
import os

# Ensure user-installed packages are on the path
site = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if site not in sys.path:
    sys.path.insert(0, site)

import uvicorn

port = int(os.environ.get("PORT", 8000))
uvicorn.run("main:app", host="0.0.0.0", port=port, loop="asyncio", http="h11")
