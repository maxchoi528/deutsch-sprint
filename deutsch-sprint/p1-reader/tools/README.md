# P1 课件自建工具

## 从文本生成切句骨架

```bash
python3 p1-reader/tools/skeleton_from_text.py article.txt --id local-article --title "Mein Text" --level B2 --output skeleton.json
```

骨架报告词数和按阅读器规则编号的句子；它不是可直接导入的完整 lesson。为保护版权与隐私，用户提供的原文放入 `p1-reader/local/`，该目录已被 `.gitignore` 排除，不要提交到公开仓库。

## 校验、合并和重建

```bash
python3 p1-reader/validate_lessons.py --file new-lesson.json
python3 p1-reader/tools/merge_lessons.py new-lesson.json
```

校验支持单篇对象、数组或 lesson 集合。合并工具只接受带 `source: "original-ai"`、`grammar_target` 和 `review_status: "ai-generated-unreviewed"` 的原创课件；用户提供的原文不能合入受跟踪的公开课件集合。合并通过后工具会重建 `p1-reader/index.html`。

## 记录导师抽检

```bash
python3 p1-reader/tools/mark_reviewed.py b2-reparaturtreff --tutor "导师姓名" --date 2026-10-24
```

日期可省略（默认今天）。该命令会写入 `reviewed_by`、`reviewed_at` 和 `review_status: "tutor-reviewed"`，然后重建阅读器。只在导师实际完成抽检后使用。
