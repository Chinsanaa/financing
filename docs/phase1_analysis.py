"""Phase 1 evaluation-integrity analysis. Read-only; writes nothing to repo."""
import sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from segment import clean_text, build_vectorizer, vectorize, tokenize, LR_HYPERPARAMS
from label import load_merchant_rules
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import accuracy_score, f1_score, classification_report

RS = 42
df = pd.read_csv("data/labeled/labeled_transactions.csv")
df = df[df["labeled"] == True].copy().reset_index(drop=True)
df["text"] = df.apply(lambda r: clean_text(r["merchant"], r["description"]), axis=1)
y = df["category"].reset_index(drop=True)
cats = sorted(y.unique())
print(f"Labeled rows: {len(df)}  |  categories: {cats}")

def cv_run(splitter, groups=None, fit_in_fold=True, label=""):
    accs, f1m, f1w = [], [], []
    yt_all, yp_all = [], []
    fold_support = []  # per-fold test support per category
    it = splitter.split(df["text"], y, groups) if groups is not None else splitter.split(df["text"], y)
    for tr, te in it:
        Xtr_txt = df["text"].iloc[tr].tolist()
        Xte_txt = df["text"].iloc[te].tolist()
        if fit_in_fold:
            vec = build_vectorizer(Xtr_txt)
        else:
            vec = build_vectorizer(df["text"].tolist())  # leaky: fit on all
        Xtr = vectorize(Xtr_txt, vec); Xte = vectorize(Xte_txt, vec)
        clf = LogisticRegression(**LR_HYPERPARAMS)
        clf.fit(Xtr, y.iloc[tr])
        yp = clf.predict(Xte)
        accs.append(accuracy_score(y.iloc[te], yp))
        f1m.append(f1_score(y.iloc[te], yp, average="macro", zero_division=0))
        f1w.append(f1_score(y.iloc[te], yp, average="weighted", zero_division=0))
        yt_all.extend(y.iloc[te]); yp_all.extend(yp)
        fold_support.append(y.iloc[te].value_counts().to_dict())
    print(f"\n=== {label} ===")
    print(f"  Accuracy : {np.mean(accs):.3f} ± {np.std(accs):.3f}")
    print(f"  F1-macro : {np.mean(f1m):.3f}")
    print(f"  F1-weight: {np.mean(f1w):.3f}")
    return np.array(yt_all), np.array(yp_all), fold_support

# ---------- ITEM 1: merchant leakage ----------
print("\n" + "#"*70 + "\n# ITEM 1: MERCHANT LEAKAGE\n" + "#"*70)
print("Does vectorized text include the merchant name? Example rows:")
for i in range(3):
    print(f"  merchant={df['merchant'].iloc[i]!r}  ->  text={df['text'].iloc[i][:50]!r}")

# a) reproduce current stratified CV (leaky vectorizer, fit-on-all)
cv_run(StratifiedKFold(5, shuffle=True, random_state=RS), fit_in_fold=False,
       label="Stratified 5-fold, vectorizer fit on ALL (reproduces eval.py)")
# b) stratified but vectorizer fit in-fold (isolates the vectorizer leak)
cv_run(StratifiedKFold(5, shuffle=True, random_state=RS), fit_in_fold=True,
       label="Stratified 5-fold, vectorizer fit in-fold (no vectorizer leak)")
# c) GroupKFold by merchant, vectorizer in-fold (honest: NEW merchants)
n_merch = df["merchant"].nunique()
print(f"\nUnique merchants: {n_merch}  (rows: {len(df)})")
gk_true, gk_pred, gk_support = cv_run(GroupKFold(n_splits=5), groups=df["merchant"], fit_in_fold=True,
       label="GroupKFold(5) by merchant, vectorizer in-fold (generalizes to NEW merchants)")
print("\nGroupKFold per-category report (out-of-fold, unseen merchants):")
print(classification_report(gk_true, gk_pred, labels=cats, zero_division=0, digits=3))

# ---------- ITEM 2: the 1.000 scores + duplicates ----------
print("\n" + "#"*70 + "\n# ITEM 2: 1.000 SCORES / TINY CLASSES / DUPLICATES\n" + "#"*70)
small = [c for c in cats if (y == c).sum() < 15]
print(f"Classes with <15 samples: {small}")
print("\nPer-fold TEST support for tiny classes under StratifiedKFold(5):")
skf_support = cv_run(StratifiedKFold(5, shuffle=True, random_state=RS), fit_in_fold=True,
                     label="(support probe)")[2]
for c in small:
    per = [fs.get(c, 0) for fs in skf_support]
    print(f"  {c:24s} stratified per-fold test support: {per}  (total {(y==c).sum()})")
for c in small:
    per = [fs.get(c, 0) for fs in gk_support]
    print(f"  {c:24s} GroupKFold  per-fold test support: {per}")

# duplicates
dup_exact = df.duplicated(subset=["merchant", "description"]).sum()
dup_text = df.duplicated(subset=["text"]).sum()
print(f"\nExact duplicate (merchant, description) rows: {dup_exact}")
print(f"Duplicate cleaned-text rows: {dup_text}")
print("\nTop repeated cleaned texts (count, text, categories):")
vc = df.groupby("text").agg(n=("text","size"), cats=("category", lambda s: sorted(set(s)))).sort_values("n", ascending=False)
for txt, row in vc[vc["n"] > 1].head(12).iterrows():
    print(f"  x{row['n']:3d}  {txt[:45]!r:48s} {row['cats']}")
# duplicates within tiny classes specifically
for c in small:
    sub = df[df["category"] == c]
    d = sub.duplicated(subset=["text"]).sum()
    print(f"  tiny-class {c:24s}: {len(sub)} rows, {d} duplicate-text, {sub['text'].nunique()} unique texts")

# ---------- ITEM 3: rule-covered vs model-only ----------
print("\n" + "#"*70 + "\n# ITEM 3: RULE-COVERED vs MODEL-ONLY\n" + "#"*70)
rules = load_merchant_rules("data/labeled/merchant_rules_expanded.csv")
def matched_by_rule(merchant):
    m = str(merchant).strip().lower()
    if m in rules:
        return True
    for pat in rules:
        if pat in m:
            return True
    return False
covered = df["merchant"].apply(matched_by_rule)
print(f"Rule-covered rows: {covered.sum()} ({100*covered.mean():.1f}%)  |  model-only rows: {(~covered).sum()} ({100*(~covered).mean():.1f}%)")
# Use GroupKFold out-of-fold predictions and split accuracy by coverage.
# Rebuild an index-aligned OOF prediction under GroupKFold to attribute per-row.
oof = pd.Series(index=df.index, dtype=object)
gk = GroupKFold(n_splits=5)
for tr, te in gk.split(df["text"], y, df["merchant"]):
    vec = build_vectorizer(df["text"].iloc[tr].tolist())
    Xtr = vectorize(df["text"].iloc[tr].tolist(), vec)
    Xte = vectorize(df["text"].iloc[te].tolist(), vec)
    clf = LogisticRegression(**LR_HYPERPARAMS); clf.fit(Xtr, y.iloc[tr])
    oof.iloc[te] = clf.predict(Xte)
acc_all = (oof.values == y.values).mean()
acc_cov = (oof[covered].values == y[covered].values).mean()
acc_mod = (oof[~covered].values == y[~covered].values).mean()
print(f"GroupKFold OOF accuracy — overall: {acc_all:.3f}")
print(f"  on RULE-COVERED merchants: {acc_cov:.3f}  (a rule already labels these; model redundant)")
print(f"  on MODEL-ONLY merchants  : {acc_mod:.3f}  <-- the real value the ML model adds")
print(f"  model-only n = {(~covered).sum()}")

# ---------- ITEM 4: label-noise sample (random 40) ----------
print("\n" + "#"*70 + "\n# ITEM 4: RANDOM 40-ROW LABEL SAMPLE (for hand audit)\n" + "#"*70)
samp = df.sample(40, random_state=RS)[["merchant", "description", "amount", "category"]]
for i, (_, r) in enumerate(samp.iterrows(), 1):
    print(f"{i:2d}. [{r['category']:20s}] {str(r['merchant'])[:28]:28s} | {str(r['description'])[:55]}")
