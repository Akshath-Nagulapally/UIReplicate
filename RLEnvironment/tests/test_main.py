import base64
import tempfile
import unittest
from pathlib import Path

import main
from PIL import Image


class PipelineHelpersTest(unittest.TestCase):
    def test_validate_requires_exactly_one_source(self):
        with self.assertRaises(ValueError):
            main._validate_source(link=None, file_path=None)

        with self.assertRaises(ValueError):
            main._validate_source(link="https://example.com", file_path="shot.png")

        self.assertEqual(main._validate_source(link="https://example.com", file_path=None), "link")
        self.assertEqual(main._validate_source(link=None, file_path="shot.png"), "file")

    def test_image_data_url_uses_file_mime_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "reference.png"
            image.write_bytes(b"png-bytes")

            data_url = main._image_data_url(image)

        encoded = base64.b64encode(b"png-bytes").decode("ascii")
        self.assertEqual(data_url, f"data:image/png;base64,{encoded}")

    def test_blank_session_payload_has_exact_prompt_and_file_part(self):
        payload = main._opencode_payload("recreate this ui", "data:image/png;base64,abc")

        self.assertEqual(payload["parts"][0], {"type": "text", "text": "recreate this ui"})
        self.assertEqual(payload["parts"][1]["type"], "file")
        self.assertEqual(payload["parts"][1]["mime"], "image/png")
        self.assertEqual(payload["parts"][1]["url"], "data:image/png;base64,abc")

    def test_apply_output_limit_updates_matching_model(self):
        config = {
            "provider": {
                "openrouter": {
                    "models": {
                        "qwen/qwen3.6-27b": {
                            "limit": {"context": 262144, "output": 2048}
                        }
                    }
                }
            }
        }

        main._apply_output_limit(config, "openrouter", "qwen/qwen3.6-27b", 384)

        self.assertEqual(
            config["provider"]["openrouter"]["models"]["qwen/qwen3.6-27b"]["limit"]["output"],
            384,
        )

    def test_run_tests_returns_mse_and_reward_for_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.jpg"
            Image.new("RGB", (1, 1), (0, 0, 0)).save(first)
            Image.new("RGB", (1, 1), (255, 255, 255)).save(second)

            result = main.run_tests(first, second, sensitivity_score=0.5)

        self.assertEqual(result["mse"], 1.0)
        self.assertAlmostEqual(result["reward"], 1.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
