#!/usr/bin/env python3
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Set, List, Any

import websockets
from websockets.server import WebSocketServerProtocol

from common import encode, decode, DEFAULT_PORT

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# In-memory state
USERS: Dict[WebSocketServerProtocol, str] = {}            # ws -> username
USERNAMES: Set[str] = set()                               # set of active usernames
ROOMS: Dict[str, Set[WebSocketServerProtocol]] = {}       # room -> set of ws subscribers

# ---- Utilities ----

def log_path_for(room: str) -> Path:
    safe = "".join(c for c in room if c.isalnum() or c in ("-", "_"))
    return LOG_DIR / f"{safe}.txt"

def append_room_log(room: str, record: Dict[str, Any]) -> None:
    p = log_path_for(room)
    line = json.dumps(record, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def tail_room_log(room: str, n: int = 50) -> List[Dict[str, Any]]:
    """Reads the last N messages from a room's log file robustly."""
    p = log_path_for(room)
    if not p.exists():
        return []
    
    lines: List[str] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Could not read log file for room {room}: {e}")
        return []

    last_lines = lines[-n:]
    out: List[Dict[str, Any]] = []
    for line in last_lines:
        try:
            if line.strip():
                out.append(json.loads(line.strip()))
        except json.JSONDecodeError:
            continue
    return out


async def broadcast(room: str, payload: Dict[str, Any], except_ws: WebSocketServerProtocol = None) -> None:
    targets = ROOMS.get(room, set()).copy()
    if except_ws:
        targets.discard(except_ws)
    if not targets:
        return
    msg = encode(payload)
    await asyncio.gather(*(ws.send(msg) for ws in targets), return_exceptions=True)

async def send(ws: WebSocketServerProtocol, payload: Dict[str, Any]) -> None:
    try:
        await ws.send(encode(payload))
    except websockets.exceptions.ConnectionClosed:
        pass # Ignore errors if connection is already closed

async def ensure_username_unique(username: str) -> bool:
    return username not in USERNAMES

async def broadcast_room_update(room: str) -> None:
    """Broadcasts the current user list for a room to all its subscribers."""
    subscribers = ROOMS.get(room, set())
    if not subscribers:
        return
    
    user_list = sorted([USERS[ws] for ws in subscribers if ws in USERS])
    payload = {"type": "room_update", "room": room, "users": user_list}
    await broadcast(room, payload)


async def handle_login(ws: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    username = data.get("username", "").strip()
    if not username:
        await send(ws, {"type":"error","action":"login","reason":"Username required"})
        return
    if not await ensure_username_unique(username):
        await send(ws, {"type":"error","action":"login","reason":"Username taken"})
        return
    
    USERS[ws] = username
    USERNAMES.add(username)
    await send(ws, {"type":"ok","action":"login"})

async def handle_subscribe(ws: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    rooms = data.get("rooms") or []
    if not isinstance(rooms, list) or not rooms:
        await send(ws, {"type":"error","action":"subscribe","reason":"rooms list required"})
        return
        
    username = USERS.get(ws)
    if not username: return

    newly_subscribed_rooms = []
    for room_str in rooms:
        room = str(room_str).strip()
        if not room: continue
        
        is_new_sub = ws not in ROOMS.get(room, set())
        ROOMS.setdefault(room, set()).add(ws)
        newly_subscribed_rooms.append(room)
        
        if is_new_sub:
            await broadcast(room, {"type":"system", "event":"join", "room":room, "username":username}, except_ws=ws)

    if newly_subscribed_rooms:
        await send(ws, {"type":"system","event":"subscribed","rooms":newly_subscribed_rooms})
    
    for room in newly_subscribed_rooms:
        history = tail_room_log(room, 50)
        if history:
            await send(ws, {"type":"history","room":room,"messages":history})
        await broadcast_room_update(room)


async def handle_unsubscribe(ws: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    rooms_to_unsub = data.get("rooms") or []
    username = USERS.get(ws)
    if not username: return
    
    unsubscribed_rooms = []
    for room in rooms_to_unsub:
        subs = ROOMS.get(room)
        if subs and ws in subs:
            subs.remove(ws)
            unsubscribed_rooms.append(room)
            if not subs:
                ROOMS.pop(room, None)
            
            await broadcast(room, {"type": "system", "event": "leave", "username": username, "room": room})
            await broadcast_room_update(room)
            
    if unsubscribed_rooms:
        await send(ws, {"type":"system","event":"unsubscribed","rooms":unsubscribed_rooms})


async def handle_publish(ws: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
    username = USERS.get(ws)
    room = str(data.get("room","")).strip()
    message = str(data.get("message","")).strip()
    if not room or not message:
        await send(ws, {"type":"error","action":"publish","reason":"room and message required"})
        return
    ts = int(time.time())
    record = {"type":"message","room":room,"username":username,"message":message,"ts":ts}
    append_room_log(room, record)
    await broadcast(room, record)

async def disconnect(ws: WebSocketServerProtocol) -> None:
    """Gracefully disconnects a user and notifies relevant rooms."""
    username = USERS.pop(ws, None)
    if not username:
        return
        
    if username in USERNAMES:
        USERNAMES.remove(username)
    
    rooms_left = []
    for room, subs in list(ROOMS.items()):
        if ws in subs:
            rooms_left.append(room)
            subs.discard(ws)
            if not subs:
                ROOMS.pop(room, None)

    for room in rooms_left:
        await broadcast(room, {"type": "system", "event": "leave", "username": username, "room": room})
        await broadcast_room_update(room)


async def handler(ws: WebSocketServerProtocol):
    """Handles the entire lifecycle of a client connection."""
    try:
        async for raw_message in ws:
            try:
                data = json.loads(raw_message)
                action = data.get("action")
            except (json.JSONDecodeError, AttributeError):
                await send(ws, {"type": "error", "reason": "Invalid JSON message format"})
                continue

            # The only action allowed before login is "login".
            # If any other action is received, send an error and wait for the next message.
            if action != "login" and ws not in USERS:
                await send(ws, {"type": "error", "reason": "Authentication required. Please log in."})
                continue

            # --- Route actions to their respective handlers ---
            if action == "login":
                if ws in USERS:
                    await send(ws, {"type": "error", "action": "login", "reason": "You are already logged in"})
                else:
                    await handle_login(ws, data)
            elif action == "subscribe":
                await handle_subscribe(ws, data)
            elif action == "unsubscribe":
                await handle_unsubscribe(ws, data)
            elif action == "publish":
                await handle_publish(ws, data)
            elif action == "logout":
                break  # Gracefully exit the loop on logout
            else:
                await send(ws, {"type": "error", "reason": f"Unknown action: '{action}'"})

    except websockets.exceptions.ConnectionClosed:
        # This is an expected exception when a client disconnects.
        pass
    except Exception as e:
        # Log any other unexpected errors that might crash a handler task.
        print(f"An unexpected error occurred for {ws.remote_address}: {e}")
    finally:
        # This block ALWAYS runs when the handler exits, ensuring cleanup.
        await disconnect(ws)

async def main():
    port = int(os.environ.get("CHAT_PORT", DEFAULT_PORT))
    print(f"Starting Chat Server on ws://0.0.0.0:{port}")
    async with websockets.serve(handler, "0.0.0.0", port, ping_interval=20, ping_timeout=20, max_queue=64):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped gracefully.")

