# 德语 B1+ → C1 冲刺工具

一套供个人离线使用的 16 周学习工具。日期默认从计划起始日 2026-10-23 开始；W0 为起始日起前三天，W1 从第 4 天开始。立即开始：[W0 三天启动清单](START_HERE.md)。

## 当前内容

1. **P6 冲刺仪表盘**：[index.html](index.html)。记录日常学习、模考和错误日志；周复盘按起始日分 W0/W1…并用“待观察 / 未触发 / 已触发”三态显示规则。W4、W9、W13 是个人内部门槛，不是 Goethe 官方评分。旧版 JSON 可导入，旧关卡勾选会安全忽略；日常打卡、模考、错误和设置保留。导出记录上次备份时间。
2. **P2 Anki 卡片工厂**：[anki-factory/README.md](anki-factory/README.md)。使用 Python 标准库，将 P1 课件 JSON 和 P6 错误日志导出为四种带 UTF-8 BOM 的 CSV；支持 `--stats`。
3. **P1 B2–C1 精读器**：[p1-reader/index.html](p1-reader/index.html)。现有 10 篇原创课件：3 篇 C1 文章、7 篇 B2/B2+ 文章。每篇至少 12 个正文词块标记，并有 3 道带证据句的理解题。所有德语内容标为「AI 生成 · 仅作练习」；7 篇新增课件仍是 `ai-generated-unreviewed`，导师抽检清单见 [review-checklist.md](p1-reader/review-checklist.md)。
4. **P3 口语教练**：[speaking-coach.md](p3-p4-prompts/speaking-coach.md)。复制到对话中使用。
5. **P4 写作批改**：[writing-coach.md](p3-p4-prompts/writing-coach.md)。复制到对话中使用。
6. **P5 跟读与听写**：[p5-shadow/README.md](p5-shadow/README.md)。服务只绑定本机地址；需要在本机安装 faster-whisper、解码依赖和模型。实现已审阅，但没有在真实安装环境运行验证。
7. **P7 缩小版补充练习**：[p7-practice/index.html](p7-practice/index.html)。包含 1 个短阅读模块、1 个双人听力脚本、共享 75 分钟的双任务 Schreiben 和 5 张 Sprechen 话题卡。Lesen/Hören 默认 20/15 分钟，与短材料量匹配；页面明确说明不是整套模考，也不用于判断考试水平。系统语音不是真实录音。

## 使用建议

- 按 [START_HERE.md](START_HERE.md) 完成 W0 基线和工具准备；官方整套模考至少保留 2 套给 W10–W13。
- 从 P1 精读中整理词块，用 P2 导入 Anki；日常记录留在 P6。
- 每周日固定导出 P6 JSON 备份。
- P1/P7 德语内容尚待导师或母语者抽检；官网可用模考套数及 P7 官网时长字段本次未联网核实。请以你报考版本的 Goethe 官网信息为准。

## 检查

在此目录运行：

```bash
bash run_checks.sh
```

脚本依次校验 P1、重建 P1/P7 页面、运行 unittest 和可选的 Playwright 浏览器冒烟测试。若没有 Playwright，冒烟测试会打印 `SKIP` 并以成功状态退出；这不代表浏览器运行时行为已验证。

所有 P1/P6/P7 本地进度保存在当前浏览器，不会同步。P2 生成本地 CSV。P5 录音只发给本机服务；模型准备和真实识别仍需在目标设备上验证。
