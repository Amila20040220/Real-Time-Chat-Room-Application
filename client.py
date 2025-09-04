#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
from typing import Optional, List

import websockets

from common import encode, decode, DEFAULT_PORT

HELP = """
Commands:
  /login <username>
  /sub <room1,room2,...>
  /unsub <room1,room2,...>
  /pub <room> <message>
  /rooms                      # list subscribed rooms (client-side)
  /quit
  /help

Notes:
- You must /login before other commands.
- After /sub, you'll receive last 5 messages for each room (if any).
"""

class Client:
    def __init__(self, uri: str):
        self.uri = uri
        self.username: Optional[str] = None
        self.rooms: List[str] = []

    async def input_loop(self, ws):
        print(HELP)
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line.startswith("/"):
                parts = line.split(" ", 2)
                cmd = parts[0].lower()
                if cmd == "/help":
                    print(HELP)
                elif cmd == "/login" and len(parts) >= 2:
                    self.username = parts[1].strip()
                    await ws.send(encode({"action":"login","username":self.username}))
                elif cmd == "/sub" and len(parts) >= 2:
                    rooms = [r.strip() for r in parts[1].split(",") if r.strip()]
                    self.rooms = sorted(set(self.rooms + rooms))
                    await ws.send(encode({"action":"subscribe","rooms":rooms}))
                elif cmd == "/unsub" and len(parts) >= 2:
                    rooms = [r.strip() for r in parts[1].split(",") if r.strip()]
                    self.rooms = [r for r in self.rooms if r not in set(rooms)]
                    await ws.send(encode({"action":"unsubscribe","rooms":rooms}))
                elif cmd == "/pub" and len(parts) >= 3:
                    room = parts[1].strip()
                    message = parts[2]
                    await ws.send(encode({"action":"publish","room":room,"message":message}))
                elif cmd == "/rooms":
                    print("Subscribed rooms:", ", ".join(self.rooms) if self.rooms else "(none)")
                elif cmd == "/quit":
                    await ws.send(encode({"action":"logout"}))
                    break
                else:
                    print("Unknown/invalid command. Type /help")
            else:
                print("Prefix commands with /. Type /help")
        try:
            await ws.close()
        except:
            pass

    async def recv_loop(self, ws):
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                print("<< invalid JSON >>")
                continue
            t = data.get("type")
            if t == "message":
                ts = time.strftime("%H:%M:%S", time.localtime(data.get("ts", 0)))
                print(f"[{ts}] #{data['room']} <{data['username']}>: {data['message']}")
            elif t == "history":
                msgs = data.get("messages", [])
                print(f"--- last {len(msgs)} messages in #{data.get('room')} ---")
                for m in msgs:
                    ts = time.strftime("%H:%M:%S", time.localtime(m.get('ts', 0)))
                    print(f"[{ts}] #{m['room']} <{m['username']}>: {m['message']}")
                print("--- end history ---")
            elif t == "system":
                ev = data.get("event","info")
                if ev == "subscribed":
                    print("Subscribed to:", ", ".join(data.get("rooms", [])))
                elif ev == "unsubscribed":
                    print("Unsubscribed from:", ", ".join(data.get("rooms", [])))
                else:
                    msg = data.get("message","")
                    if msg:
                        print(f"<< {msg} >>")
            elif t == "ok":
                print(f"<< {data.get('action','ok')} OK >>")
            elif t == "error":
                print(f"<< ERROR {data.get('action','')} - {data.get('reason','')} >>")
            else:
                print("<< unknown message >>")

    async def run(self):
        print(f"Connecting to {self.uri} ...")
        try:
            async with websockets.connect(self.uri, ping_interval=20, ping_timeout=20, max_queue=64) as ws:
                await asyncio.gather(self.input_loop(ws), self.recv_loop(ws))
        except ConnectionRefusedError:
            print("\nConnection failed. Is the server running?")
        except Exception as e:
            print(f"\nAn error occurred: {e}")


def main():
    host = os.environ.get("CHAT_HOST", "localhost")
    port = int(os.environ.get("CHAT_PORT", DEFAULT_PORT))
    uri = f"ws://{host}:{port}"
    try:
        asyncio.run(Client(uri).run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()