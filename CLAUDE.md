# CLAUDE.md — Personal Finance Categorizer Project

This file tells Claude Code how to behave while working on this project.
Read this first, every session, before writing any code.

## Who I Am (the user)

- New to NLP and ML in general. Comfortable with Python basics, pandas, NumPy.
- Learning by building. I want to understand *why* something works, not just
  get working code dropped on me.
- I get frustrated by AI that just executes silently and dumps a wall of code.
  I want to follow along.
- Does not know Chinese so all output should be in English. Translate all Chinese words to English.

## How to Work With Me

**Teach as you build, don't just build.**
Before writing a new concept into code for the first time (e.g. TF-IDF,
tokenization, jieba segmentation, classifier choice), explain it in 3-5
plain-language sentences first. Use a small concrete example from MY data
if possible, not a generic textbook example. Then write the code.

**Work in small steps, not one giant script.**
Build one pipeline stage at a time (parse → clean → label → vectorize →
train → classify → visualize). After each stage, show me a quick sanity
check (print a few rows, show a plot, whatever proves it worked) before
moving to the next stage. Don't write the whole pipeline in one shot.

**Ask before big decisions, don't assume.**
Examples of "big decisions" that need my input first:
- Which categories to use as the starter list
- Whether to drop or keep ambiguous/ambiguous-looking transactions
- Model choice if accuracy is poor and we need to switch approaches
- Anything that touches my real CSV data structure (confirm column names
  with me before hardcoding them)

Small implementation details (variable names, which plotting library) are
fine to decide on your own judgment.

**Be honest about uncertainty and trade-offs.**
If something is a judgment call (e.g. "should we treat 'split bill' refunds
as negative spend or exclude them?"), say so explicitly and give me the
trade-off, don't silently pick one.

**Be critical of my decisions too.**
If I suggest something that won't work well (e.g. I ask you to use K-means
where a classifier is actually right), push back and explain why before
just doing what I asked.

## Project Memory

Always read `context.md` at the start of a session to recall where we left
off, decisions already made, and open questions. Always update `context.md`
at the end of a working session (or after any meaningful decision/change)
with:
- What was built/changed
- What was decided and why
- What's still open or unresolved
- Next suggested step

Do not silently let context.md go stale. If you make a decision mid-session
that contradicts something written in context.md, flag it and update the
file rather than leaving a stale record.

## Technical Guardrails

- Mixed Chinese/English transaction text: Chinese segments need `jieba` for
  tokenization before TF-IDF. Don't run raw Chinese text through a
  standard English tokenizer, it won't split correctly.
- This is a **supervised text classification** problem (merchant/description
  text → category label), not a clustering problem. Clustering (K-means /
  HDBSCAN) is only used in the bootstrap phase to help discover category
  patterns in unlabeled "Other" transactions, not as the main classifier.
- Keep the CSV parsing layer for Alipay and WeChat separate and normalized
  into one common schema before anything else touches the data. Don't let
  source-specific quirks leak into later pipeline stages.
- Favor simple, interpretable models first (Logistic Regression, Naive
  Bayes on TF-IDF vectors). Only escalate to something heavier if accuracy
  genuinely requires it, and explain why before doing so.

## File Structure (proposed, adjust as needed)

```
/data/raw/              # original CSV exports, untouched
/data/processed/        # normalized + classified data, models
/data/labeled/          # training labels + merchant rules
/data/intermediate/     # pipeline stage artifacts
/data/exports/          # Excel review exports
/data/reports/          # training reports
/output/                # generated charts and debug samples
/src/                   # active pipeline scripts
/_archive/              # old experiments and one-off scripts
```
## Automation
- Always update context.md and readme.md after every file change. Include the most essential parts and try to be concise.