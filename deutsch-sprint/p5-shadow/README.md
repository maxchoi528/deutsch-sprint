# P5 · 跟读与听写工具

MVP 由 `app.py`（同机服务）和 `index.html`（网页）组成。服务只绑定 `127.0.0.1`，并只接受同源请求；音频通过本机 HTTP 接口送给本地 faster-whisper，不会上传到第三方。

## 无模型也能开始：手动听写

直接打开 `index.html`，选取自己的音频，粘贴参考文本（每句一行），用音频播放器听写，再点「对照」并导出漏听词块。此流程不依赖 Python 服务或语音识别模型；没有时间戳时，单句播放/循环按钮不可用，可用播放器手动定位。

## 自动识别：安装与启动

1. 准备 Python 3.10 或更新版本。
2. 安装 faster-whisper：

   ```bash
   python3 -m pip install faster-whisper
   ```

3. 启动本地服务：

   ```bash
   python3 app.py --model small --device cpu --compute-type int8
   ```

4. 在浏览器打开终端显示的 `http://127.0.0.1:8766/`。
5. 首次加载模型时，模型名称可能需要下载模型文件。若要完全离线运行，请先在本机准备好 Whisper 模型目录，再用 `--model /本地/模型/目录` 启动。CPU 速度取决于设备和模型大小；有 CUDA 的设备可选择 `--device cuda`。

如需从可信的 PyPI 镜像安装，可由你自行设置索引地址，不要把个人或组织镜像写进项目：

```bash
python3 -m pip install --index-url "$PIP_INDEX_URL" faster-whisper
```

模型可在网络可用时预下载到本地目录，再离线启动：

```bash
python3 -m pip install huggingface-hub
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download(repo_id="Systran/faster-whisper-small", local_dir="./models/faster-whisper-small")'
python3 app.py --model ./models/faster-whisper-small --device cpu --compute-type int8
```

需要更换 Hugging Face 访问端点时，可以在下载命令前设置 `HF_ENDPOINT`。请自行选择并验证可信端点；工具包不指定或保证任何国内镜像可用：

```bash
# 按你选择的可信端点文档先设置 HF_ENDPOINT，然后执行下载：
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download(repo_id="Systran/faster-whisper-small", local_dir="./models/faster-whisper-small")'
```

`huggingface-hub` 只用于预下载，不是跟读服务运行依赖。

### 启动自检

```bash
python3 app.py --model ./models/faster-whisper-small --selftest
```

自检导入 faster-whisper、加载所选模型，并对内置的 2 秒静音 WAV 调用一次转写，报告耗时。它只检查模型加载和音频处理通路，**不验证真实德语识别准确率或麦克风录音**。缺少 faster-whisper 时会输出中文错误并以非零状态退出。

### 常见问题

- `未安装 faster-whisper`：确认用运行服务的同一个 Python 执行 `python3 -m pip install faster-whisper`。
- 模型目录缺文件或模型加载失败：确认下载完成，并检查 `--model` 路径。
- 下载超时：优先在可联网环境预下载模型；可自行配置 `HF_ENDPOINT`，本工具不保证第三方端点可用。
- CUDA 或计算类型报错：先尝试 `--device cpu --compute-type int8`，再运行 `--selftest`。
- 麦克风不可用：检查浏览器站点权限、输入设备和 MediaRecorder 支持；自检不测试麦克风。

## 使用

- 导入你有权使用的音频和对应文本，再点「本地识别音频」生成带时间戳的语音片段。
- 选择单句播放或循环（点「停止单句循环」停止），调整 0.75×–1.25×；听写输入后点「对照」，差异会逐词标记。
- 开始跟读录音后，浏览器会请求麦克风权限；停止录音时，录音只提交到本机服务识别，并显示粗略词/分钟。
- 「导出给 P2」生成带词面标记的 JSON，可由 Anki 工厂生成 cloze 卡片。

## 三个示例场景

1. 导入一段德语播客音频和文本，精听带时间戳的句子。
2. 以 0.75× 循环播放句子，听写后检查漏词和替换词。
3. 对着参考段落跟读并录音，用本地 ASR 对照识别结果，导出漏听词块给 P2。

## 已知限制

- 需要本机安装 faster-whisper、其音频解码依赖和模型；首次下载模型时会联网下载模型文件，但音频不会离开本机。
- `--selftest` 可验证依赖、模型加载和静音音频转写调用；它不能替代真实音频/发音识别或麦克风检查。
- 跟读评分只是 ASR 文本差异和粗略语速，不评估准确发音、韵律或考试表现。
- 参考文本与 ASR 片段按顺序对齐；两者句数不同时，时间戳和参考句可能错位。
- 浏览器需支持 MediaRecorder；麦克风权限只在你点击录音时请求。
- P2 导出只带词面和上下文标记，不会自动猜中文释义或词性。

## 本机验证范围（2026-10-23）

手动听写和 P2 导出已通过 Chromium 实测。使用合成静音音频和模拟转写响应检查了单句循环、停止，以及录音转写不覆盖原材料时间戳。当前未安装 faster-whisper，真实模型、发音识别质量及物理麦克风未验证。
