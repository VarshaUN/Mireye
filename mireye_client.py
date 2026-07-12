import asyncio
import json
import os


class MireyeMCPClient:
    def __init__(self):
        self.proc = None
        self._id = 0
        self._pending = {}
        self._reader_task = None

    async def start(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        self.proc = await asyncio.create_subprocess_exec(
            "mireye-mcp",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._read_loop())

        await self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "coffee-agent", "version": "0.1"},
        })
        await self._notify("notifications/initialized", {})

    async def _read_loop(self):
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode())
            except json.JSONDecodeError:
                continue
            if "id" in msg and msg["id"] in self._pending:
                self._pending.pop(msg["id"]).set_result(msg)

    async def _send(self, method, params):
        self._id += 1
        req_id = self._id
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        await self.proc.stdin.drain()

        result = await asyncio.wait_for(fut, timeout=60)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]

    async def _notify(self, method, params):
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        await self.proc.stdin.drain()

    async def list_tools(self):
        result = await self._send("tools/list", {})
        return result["tools"]

    async def call_tool(self, name, arguments):
        result = await self._send("tools/call", {"name": name, "arguments": arguments})
        parts = result.get("content", [])
        text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
        return text

    async def close(self):
        if self.proc:
            self.proc.terminate()
            await self.proc.wait()