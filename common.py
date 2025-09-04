"""
Common helpers for message formats and constants.
"""

import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

PROTOCOL_VERSION = "1.0"
DEFAULT_PORT = 2024

# ---- Wire message helpers (JSON over WebSocket) ----

def encode(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

def decode(s: str) -> dict:
    return json.loads(s)

# ---- Message schemas (informal) ----
# Client -> Server:
# {"action":"login","username":"alice"}
# {"action":"subscribe","rooms":["general","sports"]}
# {"action":"unsubscribe","rooms":["sports"]}
# {"action":"publish","room":"general","message":"Hello world"}
# {"action":"logout"}
#
# Server -> Client:
# {"type":"ok","action":"login"} OR {"type":"error","action":"login","reason":"Username taken"}
# {"type":"system","event":"subscribed","rooms":["general"]}
# {"type":"history","room":"general","messages":[{... up to 5 ...}]}
# {"type":"message","room":"general","username":"alice","message":"Hi","ts":1700000000}
# {"type":"system","event":"info","message":"..."}  # for misc info
