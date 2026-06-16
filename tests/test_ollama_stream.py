import unittest

from simplelocalai.models import Message, OllamaClient


class OllamaStreamTests(unittest.TestCase):
    def test_iter_stream_yields_content_until_done(self) -> None:
        client = OllamaClient("qwen", {})
        lines = [
            b'{"message":{"content":"hel"},"done":false}\n',
            b'{"message":{"content":"lo"},"done":true}\n',
        ]

        self.assertEqual(list(client._iter_stream(lines)), ["hel", "lo"])

    def test_payload_includes_think_flag_when_configured(self) -> None:
        client = OllamaClient(
            "qwen",
            {
                "model": "qwen3.5:9b",
                "stream": True,
                "think": False,
                "options": {"temperature": 0.2},
            },
        )

        payload = client._payload([Message(role="user", content="hello")])

        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertEqual(payload["think"], False)
        self.assertEqual(payload["options"]["temperature"], 0.2)


if __name__ == "__main__":
    unittest.main()
