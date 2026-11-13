# CLAUDE.md: Personal Finance Categorizer

How Claude Code works on this project. Read this first, every session.

## Who I am (the user)

- New to NLP and ML. Comfortable with Python basics, pandas, NumPy.
- Learning by building: I want to understand *why* something works.
- I get frustrated by silent execution and walls of code. I want to follow along.
- I do not read Chinese. All output in English; translate any Chinese text.

## How to work with me

- **Teach as you build.** Before a concept appears in code for the first time
  (TF-IDF, tokenization, a classifier choice), explain it in 3 to 5 plain
  sentences using a small example from MY data. Then write the code.
- **Small steps.** One pipeline stage or one change at a time, each followed by
  a quick sanity check (a few rows, a test run, a screenshot).
- **Ask before big decisions:** category list changes, dropping or keeping
  ambiguous transactions, switching model approach, anything touching the real
  CSV structure or the live database. Small implementation details are yours.
- **Be honest about uncertainty.** If it is a judgment call, say so and give the
  trade-off. Do not silently pick.
- **Push back on me.** If my suggestion will not work well, explain why first.

## Project memory

- Start of session: read `docs/context.md` (short, current state).
- End of session or PR: update `docs/context.md` once (what changed, what was
  decided and why, what is open, next step). Keep it under about 200 lines;
  move older session entries to `docs/archive/SESSION_LOG.md`.
- Update `README.md` only when setup, architecture or features change.
- Read `docs/archive/` only when you need the reasoning behind an old decision.
- If a decision contradicts `docs/context.md`, flag it and fix the file.

## Technical guardrails

- **Supervised text classification**, not clustering. Clustering is only a
  bootstrap aid for unlabeled rows.
- **Chinese text needs `jieba`** before TF-IDF. Never run raw Chinese through
  an English tokenizer.
- **Parsers stay separate and normalized.** Alipay and WeChat quirks live in
  `src/parse.py` and never leak into later stages.
- **Simple models first** (Logistic Regression, Naive Bayes on TF-IDF).
  Escalate only if accuracy requires it, and explain why first.
- **Do not change `src.` vs bare import style.** Saved models depend on it.
- **Migrations are append-only.** Never edit a file in `supabase/migrations/`;
  add a new one. Never apply to the live database without my go-ahead.
- **API contract is frozen:** `docs/contracts/API_V5.md`.
- **UI rule: NO gradients, ONLY solid colors.** No glows, blurs, shadows used
  as glow, textured backgrounds, and **no purple** anywhere (charts and
  category colors included). Read `docs/DESIGN_SYSTEM.md` ("Ledger" v5) before
  touching UI. `scripts/design_gate.sh` enforces it.
- **Design skills** in `.claude/skills/`: impeccable, apple-design,
  review-animations, web-design-guidelines. Product brief: `PRODUCT.md`.
  If a skill contradicts the UI rule, the rule wins.

## Checks (run before saying "done")

```
python -m pytest tests -q                       # ML pipeline (Python 3.11)
(cd backend && python -m pytest -q)             # backend
(cd frontend && npm run typecheck && npm run lint && npm run build)
bash scripts/design_gate.sh
```
Install: `pip install -r backend/requirements-dev.txt`, `cd frontend && npm ci`.
The pins need Python 3.11. Set `MODEL2VEC_ENABLED=0` to match the server.

## Delegation (saving usage)

- Mechanical edits with exact instructions: Haiku subagent.
- Small logic changes with tests: Sonnet subagent.
- Design, risky refactors, review of every subagent diff: the main model.
- Worker rules and report format: `.claude/agents/cleanup-worker.md`.
- Never give two workers the same file. Only the main session commits.

## Where things are

`frontend/` Next.js UI · `backend/` FastAPI + `backend/tests/` · `src/` ML
pipeline · `tests/` pipeline tests · `supabase/` migrations · `docs/` memory,
design system, guides · `data/` gitignored user data. Full annotated tree:
`REPO_STRUCTURE.md`.
