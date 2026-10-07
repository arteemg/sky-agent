import asyncio
import importlib
import json
import os
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

import httpx2

from agent import loop, parallel_search, tools


class ParallelSearchTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"PARALLEL_SEARCH_ENABLED": "true"})
        self.env.start()
        importlib.reload(tools)
        self.requests = []
        self.error = False
        self.delay = False
        original_client = httpx2.AsyncClient

        async def server(request):
            self.requests.append(request)
            self.assertEqual(str(request.url), parallel_search.ENDPOINT)
            self.assertEqual(request.headers["user-agent"], parallel_search.USER_AGENT)
            self.assertNotIn("authorization", request.headers)
            payload = json.loads(request.content)
            if "id" not in payload:
                return httpx2.Response(202)
            if payload["method"] == "initialize":
                result = {
                    "protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-search", "version": "1"},
                }
            elif payload["method"] == "tools/list":
                result = {"tools": [
                    {"name": name, "inputSchema": entry["definition"]["input_schema"]}
                    for name, entry in parallel_search.TOOLS.items()
                ]}
            else:
                self.assertEqual(payload["method"], "tools/call")
                if self.delay:
                    await asyncio.sleep(1)
                result = {
                    "content": [{"type": "text", "text": "rate limit" if self.error
                                 else "Python documentation: https://docs.python.org/3/"}],
                    "isError": self.error,
                }
            return httpx2.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"], "result": result,
            })

        def client(**kwargs):
            return original_client(transport=httpx2.MockTransport(server), **kwargs)

        self.client = patch.object(parallel_search.httpx2, "AsyncClient", client)
        self.client.start()

    def tearDown(self):
        self.client.stop()
        self.env.stop()
        importlib.reload(tools)

    def test_disabled_registry_preserves_file_tools(self):
        with patch.dict(os.environ, {"PARALLEL_SEARCH_ENABLED": "false"}):
            importlib.reload(tools)
            self.assertEqual(set(tools.TOOLS), {"list_files", "read_file", "search_files"})
            self.assertIn("unknown tool", tools.run("web_search", {}))

    def test_search_fetch_and_trusted_context(self):
        for name, arguments in [
            ("web_search", {"objective": "Python docs", "search_queries": ["Python asyncio docs"]}),
            ("web_fetch", {"urls": ["https://docs.python.org/3/"]}),
        ]:
            arguments.update(session_id="untrusted", model_name="untrusted")
            output = tools.run(name, arguments, session_id="a" * 32, model_name="configured-model")
            self.assertIn("https://docs.python.org", output)
            payload = next(json.loads(request.content) for request in reversed(self.requests)
                           if json.loads(request.content).get("method") == "tools/call")
            self.assertEqual(payload["params"]["name"], name)
            self.assertEqual(payload["params"]["arguments"]["session_id"], "a" * 32)
            self.assertEqual(payload["params"]["arguments"]["model_name"], "configured-model")

    def test_mcp_error_reaches_model(self):
        self.error = True
        output = tools.run("web_fetch", {"urls": ["https://docs.python.org/3/"]})
        self.assertEqual(output, "Tool error: rate limit")

    def test_timeout_reaches_model(self):
        self.delay = True
        with patch.object(parallel_search, "TIMEOUT", 0.1):
            output = tools.run("web_fetch", {"urls": ["https://docs.python.org/3/"]})
        self.assertIn("timed out after 0.1 seconds", output)

    def test_agent_loop_dispatches_web_tools(self):
        calls = [
            NS(id="search", function=NS(name="web_search", arguments=json.dumps({
                "objective": "Python docs", "search_queries": ["Python asyncio docs"],
            }))),
            NS(id="fetch", function=NS(name="web_fetch", arguments=json.dumps({
                "urls": ["https://docs.python.org/3/"],
            }))),
        ]
        client = NS(chat=NS(completions=NS()))
        responses = iter([
            NS(choices=[NS(message=NS(content=None, tool_calls=calls))]),
            NS(choices=[NS(message=NS(content="Read the Python documentation.", tool_calls=None))]),
        ])
        model_inputs = []

        def complete(**kwargs):
            model_inputs.append(json.loads(json.dumps(kwargs)))
            return next(responses)

        client.chat.completions.create = complete
        with (
            patch.object(loop, "_get_client", return_value=client),
            patch.object(loop.memory, "add"),
            patch.object(loop.memory, "history", return_value=[{"role": "user", "content": "Python docs"}]),
        ):
            reply = loop.respond("test-chat", "Python docs", {"model": "configured-model"})
        self.assertEqual(reply, "Read the Python documentation.")
        returned = [m for m in model_inputs[1]["messages"] if m["role"] == "tool"]
        self.assertEqual(len(returned), 2)
        self.assertTrue(all("https://docs.python.org" in m["content"] for m in returned))
        arguments = [json.loads(r.content)["params"]["arguments"] for r in self.requests
                     if json.loads(r.content).get("method") == "tools/call"]
        self.assertEqual(arguments[0]["session_id"], arguments[1]["session_id"])
        self.assertEqual(arguments[0]["model_name"], "configured-model")


if __name__ == "__main__":
    unittest.main()
