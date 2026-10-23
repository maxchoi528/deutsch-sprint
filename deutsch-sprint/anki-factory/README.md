# P2 · Anki 卡片工厂

将 P1 精读 JSON 和 P6 仪表盘导出的错误日志转换成 Anki 可分别导入的 CSV。使用 Python 标准库，不需要安装依赖；没有联网或第三方 TTS 调用。

## 运行

```bash
python3 anki_factory.py sample-lesson.json sample-errors.json --output export
# 可附加 --stats 查看各类卡片数量和未标记词条
python3 anki_factory.py sample-lesson.json --output export --stats
```

在 Anki 中分别导入输出文件：

- `01-cloze.csv`：选择 **Cloze** 笔记类型，将 `Text` 映射到 Text、`Extra` 映射到 Extra。
- `02-definitions.csv`、`03-collocations.csv`、`04-errors.csv`：选择 **Basic** 笔记类型，将 `Front`、`Back` 映射到同名字段。
- 每张卡的背面包含来源 id 或日期。导入时可选择目标牌组，并勾选更新已有笔记（若需要）。
- P6 的错误日志可直接导出完整 JSON 备份后传给脚本；脚本只读取其中 `errors` 数组。也接受从「复制卡片」得到的单条 JSON，或由多条卡片组成的数组。

支持单篇课件、课件数组，以及 P1 的 `{ "lessons": [...] }` 整本课件文件。

## 卡片规则

- **Cloze**：从 P1 的 `{词面|gloss_id}` 标记定位句子，最多挖空两处；句子按句末标点切分。
- **德德释义**：`de_def` 为正面，词条（包含名词冠词、复数或 `plural_note`，以及中文提示）为背面。
- **搭配产出**：支持 `{ "prompt": "eine Entscheidung ___", "answer": "treffen" }`，也支持 `prompt → answer` 字符串；只给出完整搭配时会跳过并提示，避免猜错挖空位置。
- **错误卡**：正面使用错误原句，背面使用修正句和一句话规则。接受 P6 复制格式。
- 完全重复的卡片会去重。CSV 使用 UTF-8 BOM，便于中文导入。
- `--stats` 会显示各类去重后卡片数量，并列出课件中未用 `{词面|gloss_id}` 标记、因此没有 cloze 的词条。

## 示例数据

`sample-lesson.json` 展示了词条、无复数提示、两种搭配和阅读文本标记；`sample-errors.json` 展示了 P6 复制卡片格式。运行命令后会生成四种 CSV 示例。

## 已知限制

- 这是 CSV 工作流，不生成 `.apkg`，也不负责创建 Anki 牌组或修改 FSRS 设置。
- 本版不合成音频。可在 Anki 中按你选择且有权使用的德语 TTS 工具补充音频。
- 自动 cloze 依赖 P1 课件里的词面标记；没有对应 gloss id 的标记会被忽略。
- 搭配生成只接受明确的提示与答案，不会猜测应该挖空哪个词。
- CSV 导入字段名会受你使用的 Anki 版本和笔记类型影响；首次导入请检查预览中的正反面映射。
