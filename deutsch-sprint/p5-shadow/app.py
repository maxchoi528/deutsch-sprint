#!/usr/bin/env python3
"""Loopback-only local server for the shadowing/dictation MVP."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
MAX_AUDIO_BYTES = 120 * 1024 * 1024
MODEL = None
MODEL_LOCK = threading.Lock()
MODEL_CONFIG: dict[str, str] = {}
ALLOWED_ORIGINS: set[str] = set()


def json_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        # Avoid logging request bodies or audio filenames.
        super().log_message(fmt, *args)

    def send_json(self, status: int, value: dict) -> None:
        payload = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/transcribe":
            self.send_json(404, {"error": "未找到该本地服务接口。"})
            return
        origin = self.headers.get("Origin")
        if origin not in ALLOWED_ORIGINS:
            self.send_json(403, {"error": "拒绝非本机页面发起的请求。请从本服务显示的 localhost 页面操作。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "音频请求长度无效。"})
            return
        if length <= 0:
            self.send_json(400, {"error": "没有收到音频内容。"})
            return
        if length > MAX_AUDIO_BYTES:
            self.send_json(413, {"error": "音频超过 120 MB 限制。"})
            return
        audio = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "audio/webm").split(";", 1)[0].lower()
        suffix = {"audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/mp4": ".m4a", "audio/ogg": ".ogg", "audio/webm": ".webm"}.get(content_type, ".audio")
        language = self.headers.get("X-Audio-Language", "de").strip().lower() or "de"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="deutsch-sprint-", suffix=suffix, delete=False) as temp:
                temp.write(audio)
                temp_path = Path(temp.name)
            model = get_model()
            segments, info = model.transcribe(
                str(temp_path),
                language=language if language != "auto" else None,
                vad_filter=True,
                word_timestamps=False,
                condition_on_previous_text=False,
            )
            output = [
                {"start": round(float(segment.start), 3), "end": round(float(segment.end), 3), "text": segment.text.strip()}
                for segment in segments
                if segment.text.strip()
            ]
            self.send_json(200, {
                "language": getattr(info, "language", language),
                "duration": round(float(getattr(info, "duration", 0.0) or 0.0), 3),
                "segments": output,
            })
        except ImportError:
            self.send_json(501, {"error": "缺少 faster-whisper。请按 README 安装本地依赖后重启服务。"})
        except Exception as exc:  # Return a local diagnostic without exposing file paths.
            self.send_json(500, {"error": f"本地转写失败：{type(exc).__name__}: {exc}"})
        finally:
            if temp_path:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


def get_model():
    global MODEL
    if MODEL is not None:
        return MODEL
    with MODEL_LOCK:
        if MODEL is not None:
            return MODEL
        from faster_whisper import WhisperModel

        MODEL = WhisperModel(
            MODEL_CONFIG["model"],
            device=MODEL_CONFIG["device"],
            compute_type=MODEL_CONFIG["compute_type"],
        )
        return MODEL


def run_selftest() -> int:
    """Load the configured model and run a short, synthetic silent WAV through it."""
    global MODEL
    started = time.monotonic()
    try:
        model = get_model()
    except ImportError:
        print("自检失败：未安装 faster-whisper。请先按 p5-shadow/README.md 安装依赖。", file=__import__("sys").stderr)
        return 1
    except Exception as exc:
        print(f"自检失败：模型加载失败（{type(exc).__name__}: {exc}）。检查 --model 路径、模型文件和设备配置。", file=__import__("sys").stderr)
        return 1

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="deutsch-sprint-selftest-", suffix=".wav", delete=False) as temp:
            temp_path = Path(temp.name)
        with wave.open(str(temp_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\x00\x00" * 32000)
        segments, _info = model.transcribe(
            str(temp_path), language="de", vad_filter=True,
            word_timestamps=False, condition_on_previous_text=False,
        )
        # Consume the lazy generator so inference errors surface in this check.
        list(segments)
        print(f"自检完成：faster-whisper 与配置模型可运行；合成 2 秒静音音频转写调用成功，用时 {time.monotonic()-started:.1f} 秒。")
        print("注意：静音测试不验证真实德语识别质量或麦克风录音。")
        return 0
    except Exception as exc:
        print(f"自检失败：合成音频转写失败（{type(exc).__name__}: {exc}）。检查模型兼容性与音频后端。", file=__import__("sys").stderr)
        return 1
    finally:
        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
def main() -> None:
    parser = argparse.ArgumentParser(description="在本机启动德语跟读与听写工具")
    parser.add_argument("--host", default="127.0.0.1", help="仅建议使用 127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--model", default=os.environ.get("FASTER_WHISPER_MODEL", "small"), help="Whisper 模型名称或本地模型目录")
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda", "auto"))
    parser.add_argument("--compute-type", default="int8", help="例如 int8、float16、float32")
    parser.add_argument("--selftest", action="store_true", help="加载配置模型并对内置 2 秒静音音频运行一次转写检查")
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("出于隐私，服务只允许绑定到 loopback 地址（127.0.0.1 / localhost / ::1）。")
    MODEL_CONFIG.update(model=args.model, device=args.device, compute_type=args.compute_type)
    if args.selftest:
        raise SystemExit(run_selftest())
    url_host = f"[{args.host}]" if ":" in args.host else args.host
    ALLOWED_ORIGINS.update({f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}", f"http://{url_host}:{args.port}"})
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"本地跟读工具已启动：http://{url_host}:{args.port}/")
    print(f"音频处理：本机 faster-whisper · 模型：{args.model} · 按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止本地服务。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
