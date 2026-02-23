import asyncio

_broadcast_func = None

def set_broadcast_func(func):
    global _broadcast_func
    _broadcast_func = func

import datetime

def log_to_ui(message, type="log", metadata=None):
    global _broadcast_func
    if _broadcast_func:
        msg = {
            "type": "log",
            "log_type": type,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        # If we are in an async loop, we should use it
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(_broadcast_func(msg), loop)
            else:
                # This might not work if the loop isn't running but we can try
                pass
        except RuntimeError:
            # No event loop
            pass
