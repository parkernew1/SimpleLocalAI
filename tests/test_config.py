import tempfile
import unittest
from pathlib import Path

from simplelocalai.config import AppConfig, parse_config_value


class ConfigTests(unittest.TestCase):
    def test_parse_config_value_prefers_json(self) -> None:
        self.assertEqual(parse_config_value("0.25"), 0.25)
        self.assertEqual(parse_config_value("true"), True)
        self.assertEqual(parse_config_value('["a", "b"]'), ["a", "b"])
        self.assertEqual(parse_config_value("qwen3.5:9b"), "qwen3.5:9b")

    def test_set_dotted_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = AppConfig.load(str(path))
            config.set_dotted("qwen.options.temperature", 0.2)
            config.set_dotted("apple.helper_path", "/tmp/helper")

            self.assertEqual(config.data["models"]["qwen"]["options"]["temperature"], 0.2)
            self.assertEqual(config.data["models"]["apple"]["helper_path"], "/tmp/helper")


if __name__ == "__main__":
    unittest.main()

