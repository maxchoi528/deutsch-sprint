# 实现复审与验收记录

## 完成项

| 任务 | 结果 | 交付摘要 |
| --- | --- | --- |
| T1 | 已完成 | P1 gloss 正文标记、`validate_lessons.py` 及构建前校验。 |
| T2 | 已完成 | P1 段落容器修正；冒烟脚本检查 P1 弹窗结构和 P7 块级嵌套。 |
| T3 | 已完成 | 修正第三篇两处证据索引，并固定回归测试。 |
| T4 | 已完成 | 保留 3 篇 C1，新增 7 篇 B2/B2+；筛选等级、词条注释与导师抽检清单。 |
| T5 | 已完成 | Anki `--stats`、未标记词条提示、plural_note、CSV BOM 与 unittest。 |
| T6 | 已完成 | 起始日周次、复盘三态、内部门槛证据、旧 JSON/localStorage 迁移和备份时间提醒。 |
| T7 | 已完成 | 缩小版 P7 时长、共享写作总计时、自定义计时、双人听力与兼容迁移。 |
| T8 | 已完成 | W0 清单、周日备份、官方模考保留规则、文档和 `run_checks.sh`。 |

## 检查结果

以下在 2026-10-23 的工作区实际运行。

- `bash run_checks.sh`：退出码 0。脚本内 P1 校验器通过；P1 构建生成 10 篇；P7 构建生成 4 个模块；`unittest` 为 13 项通过；浏览器冒烟输出 `SKIP: Playwright is not installed; browser smoke tests were not run.`
- `python3 p1-reader/validate_lessons.py`：由 `run_checks.sh` 运行并通过，打印 30 道题的证据句。
- `python3 p1-reader/build_reader.py`：由 `run_checks.sh` 运行并通过，生成 10 篇课件的独立阅读器。
- `python3 p7-practice/build.py`：由 `run_checks.sh` 运行并通过，生成 4 个练习模块。
- `python3 -m unittest discover -s tests`：由 `run_checks.sh` 运行并通过，13 项测试。
- `python3 tests/smoke_browser.py`：由 `run_checks.sh` 运行；按预期跳过，Playwright 未安装，未运行浏览器实测。
- P6 和 P7 内嵌 JavaScript 使用 Node `--check` 检查：通过。
- P6、P7 JSON 与 schema 文件使用 Python `json.tool` 检查：通过。
- `git diff --check`：通过。

## 尚待处理 / 限制

- P1 德语文章、词块和释义均为 AI 生成；新增 7 篇仍标为 `ai-generated-unreviewed`。所有 P1/P7 德语内容仍待导师或母语者抽检，清单在 `p1-reader/review-checklist.md`。
- P5 的 faster-whisper、模型文件、麦克风录音与真实识别流程没有在真实安装环境运行验证。
- Playwright 未安装，所以悬停、移动端布局、P6 旧备份迁移和 P7 计时交互虽然已有冒烟用例，仍未实际由浏览器执行。
- P7 `official_duration_minutes` 与 Goethe 官网可用完整模考套数本次未联网核实。界面和文档明确标注时长待核实；W10–W13 至少保留 2 套的建议按用户计划保留。
- P7 的听力是系统语音合成，不是真实录音；是否可用、是否有两种德语音色取决于设备与系统语音服务。
