import contextlib
import io
import sys
import unittest
from unittest.mock import patch

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "p5-shadow"))
import app as shadow_app  # noqa: E402


class P5SelftestTests(unittest.TestCase):
    def tearDown(self):
        shadow_app.MODEL = None
        shadow_app.MODEL_CONFIG.clear()

    def test_missing_faster_whisper_has_chinese_error_and_nonzero_result(self):
        shadow_app.MODEL = None
        shadow_app.MODEL_CONFIG.update(model="local-model", device="cpu", compute_type="int8")
        stderr = io.StringIO()
        with patch.dict(sys.modules, {"faster_whisper": None}), contextlib.redirect_stderr(stderr):
            result = shadow_app.run_selftest()
        self.assertEqual(result, 1)
        self.assertIn("未安装 faster-whisper", stderr.getvalue())
        self.assertIn("README.md", stderr.getvalue())

    def test_selftest_runs_two_second_synthetic_audio(self):
        class Model:
            def transcribe(self, path, **kwargs):
                import wave
                with wave.open(path, "rb") as audio:
                    self_rate = audio.getframerate()
                    duration = audio.getnframes() / self_rate
                self.asserted = (duration, kwargs)
                return iter(()), object()

        mock_model = Model()
        shadow_app.MODEL = mock_model
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = shadow_app.run_selftest()
        self.assertEqual(result, 0)
        self.assertAlmostEqual(mock_model.asserted[0], 2.0)
        self.assertIn("不验证真实德语识别质量或麦克风", output.getvalue())


if __name__ == "__main__":
    unittest.main()
