import asyncio
import unittest

from app.websocket_manager import WebSocketManager


class FakeSocket:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    async def send_json(self, payload):
        await asyncio.sleep(0)
        if self.fail:
            raise RuntimeError("disconnected")
        self.messages.append(payload)


class WebSocketManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_to_many_tabs_and_drop_failed_socket(self):
        manager = WebSocketManager()
        good = [FakeSocket() for _ in range(20)]
        bad = FakeSocket(fail=True)
        manager.active.update([*good, bad])
        await manager.broadcast({"event": "state_update", "summary": {"count": 1}})
        self.assertEqual(manager.connection_count, 20)
        self.assertEqual(manager.broadcast_count, 1)
        self.assertTrue(all(len(socket.messages) == 1 for socket in good))


if __name__ == "__main__":
    unittest.main()
