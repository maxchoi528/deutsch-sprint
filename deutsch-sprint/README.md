# 德语 B1+ → C1 冲刺工具

一套供个人离线使用的 16 周学习工具。日期默认从计划起始日 2026-10-23 开始；W0 为起始日起前三天，W1 从第 4 天开始。立即开始：[W0 三天启动清单](START_HERE.md)。若在 2026-10-24 开始学习，先在仪表盘「设置」保存这个起始日；已有记录不会被自动改写。

## 当前内容

1. **P6 冲刺仪表盘**：[index.html](index.html)。记录日常学习、模考和错误日志；总览新增 16 周 syllabus 任务卡，包含语法、P1 推荐课件（点击直达）、口语、写作、复盘和五项今日任务。任务勾选与当日打卡一起存储。周复盘按起始日分 W0/W1…并用三态显示规则。W4、W9、W13 是个人内部门槛，不是 Goethe 官方评分。旧版 JSON 可导入，旧关卡勾选会安全忽略；导出记录上次备份时间。
   错误日志支持粘贴 P3/P4 Markdown 或 TSV 错误表，预览后去重导入；复制提示词按钮会复制对应完整 Markdown 文件。
2. **P2 Anki 卡片工厂**：[anki-factory/README.md](anki-factory/README.md)。使用 Python 标准库，将 P1 课件 JSON 和 P6 错误日志导出为四种带 UTF-8 BOM 的 CSV；支持 `--stats`。
3. **P1 B2–C1 精读器**：[p1-reader/index.html](p1-reader/index.html)。现有 10 篇原创课件：3 篇 C1 文章、7 篇 B2/B2+ 文章。每篇至少 12 个正文词块标记，并有 3 道带证据句的理解题。新增 B2/B2+ 文章已补齐中文释义、实际摘要、语法提示和搭配产出；首次使用默认进入 B2。所有德语内容标为「AI 生成 · 仅作练习」；7 篇新增课件仍是 `ai-generated-unreviewed`，导师抽检清单见 [review-checklist.md](p1-reader/review-checklist.md)。
4. **P3 口语教练**：[speaking-coach.md](p3-p4-prompts/speaking-coach.md)。复制到对话中使用。
5. **P4 写作批改**：[writing-coach.md](p3-p4-prompts/writing-coach.md)。复制到对话中使用。
6. **P5 跟读与听写**：[p5-shadow/README.md](p5-shadow/README.md)。服务只绑定本机地址；需要在本机安装 faster-whisper、解码依赖和模型。手动听写与 P2 导出已在浏览器实测；自动识别尚未安装模型，真实 ASR 和物理麦克风仍未验证。
7. **P7 缩小版补充练习**：[p7-practice/index.html](p7-practice/index.html)。包含短阅读、双人市民对话、采访、讲座式听力、共享 75 分钟的双任务 Schreiben 和配对口试话题卡。Lesen/Hören 小练默认时长与材料量匹配；页面明确说明不是整套模考，也不用于判断考试水平。系统语音不是真实录音。

## 使用建议

- 按 [START_HERE.md](START_HERE.md) 完成 W0 基线和工具准备；先核实官方材料数量，再按启动清单保留未做过的完整套题给 W10–W13。
- 从 P1 精读中整理词块，用 P2 导入 Anki；日常记录留在 P6。
- 每周日固定导出 P6 JSON 备份。
- 每天可从 P6 总览“本周任务”勾选 5 个学习块；计划源文件为 `syllabus.json`，修改后运行 `python3 build_dashboard.py`。
- P1/P7 德语内容尚待导师或母语者抽检；官网可用模考套数及 P7 官网时长字段本次未联网核实。请以你报考版本的 Goethe 官网信息为准。

## 检查

在此目录运行：

```bash
REQUIRE_BROWSER=1 bash run_checks.sh
```

脚本依次校验 P1、重建 P1/P7 页面、运行 unittest 和 Playwright 浏览器检查。上面的严格模式在浏览器不可用时会失败。若只运行 `bash run_checks.sh`，没有 Playwright 或 Chromium 时会打印 `SKIP`；这种退出码 0 不代表界面已通过验证。

2026-10-23 本机实测：14 项 unittest 与 Chromium 浏览器检查均通过，未跳过浏览器。覆盖旧 JSON 文件导入、打卡、关卡、三态与历史周复盘、备份到 Anki、P1 桌面/手机弹窗、盲读、P7 共享/自定义计时、直接打开本地 HTML，以及 P5 手动听写。P5 自动识别交互使用模拟响应，不能当作真实识别验证。完整结果见 [REVIEW_REPORT.md](REVIEW_REPORT.md) 和 [CHECK_RESULTS.txt](CHECK_RESULTS.txt)。

所有 P1/P6/P7 本地进度保存在当前浏览器，不会同步。P2 生成本地 CSV。P5 录音只发给本机服务；模型准备和真实识别仍需在目标设备上验证。
