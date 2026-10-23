# 德语 B1+ → C1 冲刺工具

按原计划的开发顺序搭起本地学习工具。日期默认从计划制定日 2026-10-23 开始；W0 为三天诊断与装机，W1 从 2026-10-26 开始。

为满足计划“学习块之间至少休息 15 分钟”的规则，仪表盘将精读移至 09:45、写作移至 15:45；这样能在 Anki 后和精听后留出休息时间。

立即开始：[W0 三天启动清单](START_HERE.md)。

## 当前交付

1. **P6 冲刺仪表盘**：打开 [index.html](index.html)，记录日常学习、模考、错误、关卡与周复盘。
2. **P2 Anki 卡片工厂**：见 [anki-factory/README.md](anki-factory/README.md)，把 P1 导出的课件 JSON 和 P6 导出的错误日志转成四种 CSV。
3. **P1 C1 精读课件**：打开 [p1-reader/index.html](p1-reader/index.html)，从三篇原创样例开始练习；可导出单篇 JSON 给 P2。
4. **P3 口语教练**：复制 [speaking-coach.md](p3-p4-prompts/speaking-coach.md) 到对话中使用。
5. **P4 写作批改**：复制 [writing-coach.md](p3-p4-prompts/writing-coach.md) 到对话中使用。
6. **P5 跟读与听写**：见 [p5-shadow/README.md](p5-shadow/README.md)。需要你本机安装本地 ASR 依赖后运行；音频只发给同机 localhost 服务。
7. **P7 补充模考**：打开 [p7-practice/index.html](p7-practice/index.html)，包含原创 Lesen/Hören 练习、两道 Schreiben 任务和五张 Sprechen 话题卡。

## 建议启动顺序

- 先做 P6 诊断记录，再用 P3/P4 建立每日输出反馈。
- 从 P1 样例精读中整理词块，用 P2 每天追加到 Anki。
- 需要音频精练时再启动 P5。
- 第 6–8 周根据实际考点和证书用途确认报名安排；仪表盘不会替你决定考试资格或官方成绩。

各模块 README 记录使用说明、示例和限制。P6、P1、P7 的练习记录保存在当前浏览器；P2 生成本地 CSV；P5 的音频只送到同机服务，处理后删除临时文件。
