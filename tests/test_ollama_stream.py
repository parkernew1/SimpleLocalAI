import unittest

from simplelocalai.models import OllamaClient


class OllamaStreamTests(unittest.TestCase):
    def test_iter_stream_yields_content_until_done(self) -> None:
        client = OllamaClient("qwen", {})
        lines = [
            b'{"message":{"content":"hel"},"done":false}\n',
            b'{"message":{"content":"lo"},"done":true}\n',
        ]

        self.assertEqual(list(client._iter_stream(lines)), ["hel", "lo"])


if __name__ == "__main__":
    unittest.main()

