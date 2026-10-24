# P1 · B2–C1 精读课件

`index.html` 是可离线打开的独立阅读器。内容源保存在 `lessons.json`，界面模板在 `reader.template.html`；修改 JSON 后运行 `python3 build_reader.py` 可重新生成独立页面。

## 使用方法

1. 直接打开 `index.html`。
2. 首次默认打开 B2 文章；也可按等级筛选。鼠标悬停、键盘聚焦或点按带下划线的词块可查看中文、德德释义、词形和搭配。
3. 先使用「盲读模式」读全文，再答题并提交；提交后才显示答案与证据句，涉及多个句子的证据会同时高亮。
4. 「显示中文摘要」默认隐藏。每篇的盲读自测次数与最近分数保存在当前浏览器。
5. 点击「导出本篇 JSON」，可把当前文章送入 P2 Anki 卡片工厂。也可导入符合 `lesson.schema.json` 结构的单篇或多篇 JSON。

## 示例内容

当前包含 16 篇练习：3 篇 C1、13 篇 B2/B2+。新增的 6 篇每篇 220–320 词，练习 Passiv、Konjunktiv II/I（明确标注虚构的访谈整理）、Nominalstil、Partizipialattribute 与 Funktionsverbgefüge；体裁包括虚构报道、读者来信、访谈整理、评论、经验分享和说明文。每篇至少 12 个正文词块和 3 道理解题。

所有内置文本均为 AI 生成的原创练习并标记「AI 生成 · 仅作练习」，不冒充真实新闻或访谈，不使用真实具名引语；报导中的练习数字明确标为虚构。13 篇新增课件标为 `ai-generated-unreviewed`；抽检重点见 [review-checklist.md](review-checklist.md)。正式用于备考前，请让导师或母语者抽检德语表达。

## 自建课件流程

1. 复制 [AUTHORING_PROMPT.md](AUTHORING_PROMPT.md)，输入主题或你有权使用的自有文本。用户提供的原文请放在 `local/`（已加入 `.gitignore`），不要推送到公开仓库。
2. 保存输出为单篇 JSON，运行 `python3 validate_lessons.py --file /path/to/new-lesson.json`。
3. 原创 AI 课件校验通过后，运行 `python3 tools/merge_lessons.py /path/to/new-lesson.json`；工具会检查重复 ID、整篇集合并重建页面。用户提供的原文不会被合并到公开课件集合。
4. 导师实际完成抽检后，运行 `python3 tools/mark_reviewed.py LESSON_ID --tutor "姓名" --date YYYY-MM-DD` 记录签核并重建页面。
5. 从纯文本建立带词数和切句索引的草稿，可用 `python3 tools/skeleton_from_text.py article.txt --id draft-id --title "标题" --output skeleton.json`。

## 数据格式

- `lessons.json` 是内容源，字段按 `lesson.schema.json` 定义。
- 词块使用 `{词面|gloss_id}` 标记；词条可用 `cefr` 标注 B2、C1 或固定搭配/词块。题目可用 `evidence_sentence_indices` 指向一个或多个证据句；旧版 `evidence_sentence_index` 仍兼容。
- 单选题包含细节、推断与立场题型；B2+/C1 课件至少包含一道推断或立场题。
- 生成器把 JSON 嵌入 HTML 的 `application/json` 数据块，阅读器启动时解析该 JSON，不需要网络、第三方库或服务器。

## 已知限制

- 目前提供 16 篇课件，尚未覆盖完整的主题语料库；新增 B2/B2+ 文本仍待导师抽检。
- 题目按答案文本精确匹配；「选择（细节）」是普通单选题标签，不是独立配对交互。
- 盲读分数只保存在当前浏览器，不含独立备份/导出功能。
- 导入时做必需字段检查；需要完整校验时可用 JSON Schema 2020-12 验证 `lesson.schema.json`。
- 标注词块的语法、词形、搭配和释义仍需导师或母语者抽检。
