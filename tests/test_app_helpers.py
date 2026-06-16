import unittest

from simplelocalai.app import parse_context_tokens


class AppHelperTests(unittest.TestCase):
    def test_parse_context_tokens_accepts_k_suffix(self) -> None:
        self.assertEqual(parse_context_tokens("16k"), 16384)
        self.assertEqual(parse_context_tokens("32K"), 32768)

    def test_parse_context_tokens_accepts_integer_tokens(self) -> None:
        self.assertEqual(parse_context_tokens("32768"), 32768)

    def test_parse_context_tokens_rejects_tiny_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_context_tokens("512")


if __name__ == "__main__":
    unittest.main()

