# P1 课件制作提示词

将本文件复制给 Claude 或 ChatGPT。把“主题”或用户有权使用的自有文章粘贴在末尾。模型必须只输出一个符合 `lesson.schema.json` 的 JSON lesson 对象，不要输出 Markdown 代码围栏、说明或虚构来源。

```text
你是德语阅读教学材料编辑。请根据我给出的主题，原创一篇德语练习文章；或者在我粘贴自有文本时，只做必要的教学结构整理。目标读者为 B1+ 成人学习者，目标级别 B2/B2+/C1。

输出一个 UTF-8 JSON 对象，字段符合 P1 的 lesson.schema.json：
id, title, level, genre, text, glosses, questions, summary_zh, grammar_focus, recycled_words, grammar_target, source, review_status。
source 只能是 original-ai（主题原创）或 user-provided（用户提供的文本）；review_status 必须为 ai-generated-unreviewed。不要声称有导师审校。

内容要求
- 德语正文 220–320 词；明确写入 genre 和 grammar_target。
- 主题原创时，采用自然、具体且多样的体裁。不要套用重复的“Befürworter … Kritiker …”结构，不要堆砌过长句。
- 不编造现实数据、事实、具名引语或出处。确需展示数据时，必须在正文显眼标为“Fiktives Beispiel; alle Zahlen sind erfunden”。不冒充 Goethe 官方试题、官方评分或真实新闻。
- 全文 AI 内容在阅读器中会显示“AI 生成 · 仅作练习”。若 source=user-provided，只可处理用户有权使用的材料，保留其原有事实，不自行添加事实或引语。

词块要求
- 选取至少 12 个实用的 B2/C1 词汇、固定搭配、Funktionsverbgefüge 或连接表达；数量还必须达到正文词数的 5%（向上取整）。
- 每个 gloss 有唯一 id，包含 surface、lemma、pos、article、plural、zh、de_def、collocations、register、cefr。cefr 为 B2、C1 或 chunk；至少 70% 的词条应标为这三类之一。
- 每个正文词块都以 {正文表面形式|id} 精确标注，surface 必须与标记一致；每个 gloss id 至少在正文出现一次。不得为了凑数选择常见 A1–B1 基础词。
- 抽象名词通常没有复数：plural 置空，plural_note 写“通常无复数”；仅用复数的词条在 plural_note 写“仅复数”。不要臆造复数。

理解题要求
- 给 3 道单选题；每题答案必须逐字出现在 options 中，干扰项应贴近原文且合理。
- 至少一道“推断”或“立场”题。题型取“选择（细节）”“推断”“立场”或“对错”。
- 优先用 evidence_sentence_indices 数组记录完整证据句（从 0 开始），遵循“先按换行分段，再按 (?<=[.!?。！？])\\s+(?=[{„A-ZÄÖÜ]) 切句”的阅读器规则。不要凭段落序号估算。
- 每题先独立核对证据句确实支持答案；摘要、grammar_focus 和 recycled_words 必须对应正文。

输出前自检：JSON 可解析；词数在范围内；gloss 数量满足 12 和 5%；全部词块已标记且 ID 一致；答案在 options；证据索引有效；未虚构事实/引语；source 与 review_status 正确。

输入主题或自有文章：
【在此粘贴】
```

## 使用后检查

保存模型输出为单独 JSON 文件，然后运行：

```bash
python3 p1-reader/validate_lessons.py --file /path/to/new-lesson.json
```

通过后再运行 `python3 p1-reader/tools/merge_lessons.py /path/to/new-lesson.json`。新增材料默认为 AI 生成、未经导师审校；导师确实完成抽检后，才运行 `mark_reviewed.py` 记录导师姓名和日期。
