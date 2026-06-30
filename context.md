# context.md — Project Memory & Explainer

This file is the running record of the project: what it is, what's been
decided, what's open, and what's next. Claude Code should read this at the
start of every session and update it at the end.

---

## The Problem

While living in China, expenses were split across Alipay and WeChat Pay.
Neither app gives a clean combined view of spending, and manually
categorizing transactions (Food, Transport, Shopping, etc.) from exported
CSVs was too time-consuming to keep up with. Using AI chat tools to
categorize transactions ad hoc was inconsistent and didn't generalize.

## The Goal

A pipeline that:
1. Takes multiple CSV exports (Alipay + WeChat, possibly more sources later)
2. Automatically categorizes each transaction
3. Visualizes spending (by category, over time, by merchant)
4. Improves with use, instead of needing manual re-categorization every time

## Why This Is a Classification Problem, Not Clustering

Early instinct was to use K-means clustering. Worth remembering why that's
not the right primary tool:

- K-means is **unsupervised**. It groups similar transactions together but
  has no concept of category names like "Food" or "Transport." You'd have
  to manually interpret and label every cluster, every time you re-run it,
  and clusters can shift between runs.
- The category names we actually want (Food, Transport, Rent, etc.) are
  known to us in advance. That's a supervised learning setup: we have
  labels we want predicted, so we train a **classifier**.
- Clustering still has a role: as a **bootstrap/discovery tool**, to look
  at unlabeled "Other" transactions and surface groupings we hadn't
  thought of yet. After that, those groups get manually labeled and folded
  into the classifier's training data.

## Key Decisions Made So Far

| Decision | Choice | Why |
|---|---|---|
| Categorization approach | Supervised text classification (not pure clustering) | We know our target categories in advance |
| Category list strategy | Mix: start with a rough manual list, use clustering on "Other" bucket to discover more | User wants both control and discovery |
| Transaction text language | Mixed Chinese and English | Confirmed by user; needs special handling |
| Chinese tokenization | `jieba` library | Standard tool for Chinese word segmentation; raw text won't tokenize correctly with English-only tools |
| Feature extraction | TF-IDF on segmented/tokenized text | Simple, interpretable, doesn't require heavy compute |
| Model choice (starting point) | Logistic Regression or Naive Bayes | Fast, interpretable, good baseline for text classification; escalate only if needed |
| Training data | Manually label ~200-500 transactions as a starting set | No way around needing some labeled data for supervised learning |

## Key Terms (for reference, written in plain language)

- **Tokenization**: splitting text into individual word units. Trivial for
  English (split on spaces), but Chinese needs a dedicated tool since there
  are no spaces between words.
- **TF-IDF**: a way to convert text into numbers a model can learn from. It
  weights words by how distinctive they are to a specific transaction
  relative to all transactions (common filler words score low, distinctive
  merchant names score high).
- **Classifier**: a model trained on labeled examples (text -> category) that
  then predicts categories for new, unseen text.
- **Bootstrap labeling**: using a faster but rougher method (like clustering)
  to get an initial set of labels, refined by hand, before training the
  real classifier.

## Open Questions / Not Yet Decided

- [ ] Exact starter category list (need user's rough list)
- [ ] Exact column structure of Alipay export CSV (need a sample)
- [ ] Exact column structure of WeChat export CSV (need a sample)
- [ ] How to handle refunds / transfers between own accounts (exclude from
      spend totals? separate category?)
- [ ] Visualization tool: Streamlit dashboard vs. static matplotlib/plotly
      charts (leaning Streamlit for interactivity, not yet confirmed)

## Next Suggested Step

Get a sample (even anonymized/few rows) of both the Alipay and WeChat CSV
exports so the parser in Step 1 can be built against real column structures
instead of assumptions.

## Session Log

### Session 0 (planning, before Claude Code)
- Defined the problem and goal
- Corrected initial K-means-only idea to supervised classification +
  clustering-as-bootstrap hybrid
- Confirmed: mixed Chinese/English text, user new to NLP, wants
  teaching-style collaboration
- Created CLAUDE.md and this context.md
- No code written yet
