# 德语 B1+ → C1 冲刺工具

一套供个人离线使用的 16 周学习工具。首次打开 P6 时选择计划起始日（默认今天）；W1 从起始日 +2 天当日或之后的第一个周一开始，因此 W0 为 2–8 天，之后按周一至周日计算。立即开始：[W0 三天启动清单](START_HERE.md)。

## 当前内容

1. **P6 冲刺仪表盘**：[index.html](index.html)。记录日常学习、模考和错误日志；总览新增 16 周 syllabus 任务卡，包含语法、P1 推荐课件（点击直达）、口语、写作、复盘和五项今日任务。任务勾选与当日打卡一起存储。周复盘按起始日分 W0/W1…并用三态显示规则。W4、W9、W13 是个人内部门槛，不是 Goethe 官方评分。旧版 JSON 可导入，旧关卡勾选会安全忽略；导出记录上次备份时间。
   错误日志支持粘贴 P3/P4 Markdown 或 TSV 错误表，预览后去重导入；复制提示词按钮会复制对应完整 Markdown 文件。
2. **P2 Anki 卡片工厂**：[anki-factory/README.md](anki-factory/README.md)。使用 Python 标准库，将 P1 课件 JSON 和 P6 错误日志导出为四种带 UTF-8 BOM 的 CSV；支持 `--stats`。
3. **P1 B2–C1 精读器**：[p1-reader/index.html](p1-reader/index.html)。现有 16 篇课件：3 篇 C1、13 篇 B2/B2+。每篇至少 12 个正文词块并有 3 道带证据句的理解题。新增 6 篇分别练习 Passiv、Konjunktiv II/I、Nominalstil、Partizipialattribute、Funktionsverbgefüge，并提供单篇校验、合并重建和导师抽检记录工具。六篇均为 `ai-generated-unreviewed`；审校清单见 [review-checklist.md](p1-reader/review-checklist.md)。所有内容需在正式备考前由导师或母语者抽检。
4. **P3 口语教练**：[speaking-coach.md](p3-p4-prompts/speaking-coach.md)。复制到对话中使用。
5. **P4 写作批改**：[writing-coach.md](p3-p4-prompts/writing-coach.md)。复制到对话中使用。
6. **P5 跟读与听写**：[p5-shadow/README.md](p5-shadow/README.md)。服务只绑定本机地址；需要在本机安装 faster-whisper、解码依赖和模型。`--selftest` 检查依赖、模型初始化和静音音频调用；它不验证真实识别质量或麦克风。手动听写与 P2 导出已在浏览器实测。
7. **P7 缩小版补充练习**：[p7-practice/index.html](p7-practice/index.html)。包含短阅读、市民对话、采访、讲座式听力、共享 75 分钟的双任务 Schreiben 和配对口试话题卡。Lesen/Hören 练习时长与短材料量匹配；参考官方时长为阅读 65、听力约 40、写作 75、配对口试约 20 分钟（单人口试约 15 分钟），写作 75 分钟是两个任务合计。页面明确说明不是整套模考，也不用于判断考试水平。系统语音不是真实录音。

## 使用建议

- 按 [START_HERE.md](START_HERE.md) 完成 W0 基线和工具准备；先核实官方材料数量，再按启动清单保留未做过的完整套题给 W10–W13。
- 从 P1 精读中整理词块，用 P2 导入 Anki；日常记录留在 P6。
- 每周日固定导出 P6 JSON 备份。
- 每天可从 P6 总览“本周任务”勾选 5 个学习块；计划源文件为 `syllabus.json`，修改后运行 `python3 build_dashboard.py`。
- P1/P7 德语内容尚待导师或母语者抽检；Goethe 官方完整模考实际可用套数仍未核实。P7 时长参考《Durchführungsbestimmungen Goethe-Zertifikat C1》，报考前请按考点当期信息复核。

## 检查

在此目录运行：

```bash
REQUIRE_BROWSER=1 bash run_checks.sh
```

脚本依次校验 P1 和 syllabus、构建 P6/P1/P7、检查生成的 P1/P7 页面没有未提交漂移、运行 unittest 和 Playwright 浏览器检查。`REQUIRE_BROWSER=1` 在浏览器不可用时失败；普通模式缺少 Playwright 或 Chromium 时会打印 `SKIP`，这不代表界面已通过验证。

最近一次验收的准确命令、退出码、测试数量和浏览器覆盖范围记录在 [CHECK_RESULTS.txt](CHECK_RESULTS.txt)；任务明细与未验证项见 [REVIEW_REPORT.md](REVIEW_REPORT.md)。

所有 P1/P6/P7 本地进度保存在当前浏览器，不会同步。P2 生成本地 CSV。P5 录音只发给本机服务；模型准备和真实识别仍需在目标设备上验证。
