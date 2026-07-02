"""Phase 4: confidence calibration + honest tuning, evaluated under GroupKFold.

Read-only; prints tables. No personal data is written to the repo.
"""
import sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from segment import clean_text, build_vectorizer, vectorize, tokenize, LR_HYPERPARAMS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import accuracy_score, f1_score

RS = 42
df = pd.read_csv("data/labeled/labeled_transactions.csv")
df = df[df["labeled"] == True].copy().reset_index(drop=True)
df["text"] = df.apply(lambda r: clean_text(r["merchant"], r["description"]), axis=1)
y = df["category"].reset_index(drop=True)
texts = df["text"].tolist()
groups = df["merchant"].values


def make_vectorizer(max_features=3000, ngram_range=(1, 2), min_df=2, max_df=0.8):
    return TfidfVectorizer(tokenizer=tokenize, max_features=max_features,
                           ngram_range=ngram_range, min_df=min_df, max_df=max_df,
                           lowercase=False)


def oof_predict(splitter, use_groups, C=10, **vec_kw):
    """Return out-of-fold (y_true, y_pred, confidence) arrays."""
    yt, yp, conf = [], [], []
    it = splitter.split(texts, y, groups) if use_groups else splitter.split(texts, y)
    hp = dict(LR_HYPERPARAMS); hp["C"] = C
    for tr, te in it:
        vec = make_vectorizer(**vec_kw)
        vec.fit([texts[i] for i in tr])
        Xtr = vec.transform([texts[i] for i in tr])
        Xte = vec.transform([texts[i] for i in te])
        clf = LogisticRegression(**hp); clf.fit(Xtr, y.iloc[tr])
        proba = clf.predict_proba(Xte)
        yt.extend(y.iloc[te]); yp.extend(clf.predict(Xte)); conf.extend(proba.max(axis=1))
    return np.array(yt), np.array(yp, dtype=object), np.array(conf)


def reliability(yt, yp, conf, label):
    correct = (yt == yp).astype(int)
    print(f"\n--- Reliability: {label} ---")
    print(f"  overall acc={correct.mean():.3f}  mean_conf={conf.mean():.3f}")
    print(f"  {'conf bin':12s} {'n':>5s} {'accuracy':>9s} {'mean conf':>10s} {'gap':>7s}")
    ece = 0.0
    for lo in np.arange(0.0, 1.0, 0.1):
        hi = lo + 0.1
        m = (conf >= lo) & (conf < hi) if hi < 1.0 else (conf >= lo) & (conf <= hi)
        n = int(m.sum())
        if n == 0:
            continue
        acc = correct[m].mean(); mc = conf[m].mean()
        ece += (n / len(conf)) * abs(acc - mc)
        print(f"  [{lo:.1f},{hi:.1f})   {n:5d} {acc:9.3f} {mc:10.3f} {acc-mc:+7.3f}")
    print(f"  ECE (expected calibration error): {ece:.3f}")
    return correct


def threshold_analysis(yt, yp, conf, label, thr=0.70):
    correct = (yt == yp).astype(int)
    auto = conf >= thr
    rev = ~auto
    print(f"\n--- Threshold {thr} on {label} ---")
    print(f"  AUTO-ACCEPT (conf>= {thr}): {auto.sum():4d} rows ({100*auto.mean():.1f}%), "
          f"accuracy {correct[auto].mean() if auto.sum() else float('nan'):.3f}")
    print(f"  ROUTE-TO-REVIEW (conf< {thr}): {rev.sum():4d} rows ({100*rev.mean():.1f}%), "
          f"accuracy {correct[rev].mean() if rev.sum() else float('nan'):.3f}")
    if auto.sum():
        wrong_auto = int((~correct[auto].astype(bool)).sum())
        print(f"  Wrong predictions auto-accepted (silent errors): {wrong_auto}")


print("#"*70 + "\n# PHASE 4: CALIBRATION\n" + "#"*70)
skf = StratifiedKFold(5, shuffle=True, random_state=RS)
gkf = GroupKFold(5)
yt_s, yp_s, c_s = oof_predict(skf, use_groups=False)
yt_g, yp_g, c_g = oof_predict(gkf, use_groups=True)
reliability(yt_s, yp_s, c_s, "Stratified CV (leaky: known merchants)")
reliability(yt_g, yp_g, c_g, "GroupKFold CV (honest: NEW merchants)")
threshold_analysis(yt_s, yp_s, c_s, "Stratified CV")
threshold_analysis(yt_g, yp_g, c_g, "GroupKFold CV")

print("\n" + "#"*70 + "\n# PHASE 4: TUNING GRID (judged on GroupKFold)\n" + "#"*70)
grid = [
    dict(C=10, max_features=3000, ngram_range=(1, 2)),  # current production
    dict(C=1.0, max_features=3000, ngram_range=(1, 2)),
    dict(C=0.5, max_features=3000, ngram_range=(1, 2)),
    dict(C=10, max_features=3000, ngram_range=(1, 1)),  # unigrams only
    dict(C=10, max_features=1000, ngram_range=(1, 2)),
    dict(C=10, max_features=5000, ngram_range=(1, 3)),
]
print(f"{'config':50s} {'strat acc':>9s} {'strat f1m':>9s} {'group acc':>9s} {'group f1m':>9s}")
for cfg in grid:
    C = cfg.pop("C")
    yt, yp, _ = oof_predict(skf, use_groups=False, C=C, **cfg)
    sa, sf = accuracy_score(yt, yp), f1_score(yt, yp, average="macro", zero_division=0)
    yt2, yp2, _ = oof_predict(gkf, use_groups=True, C=C, **cfg)
    ga, gf = accuracy_score(yt2, yp2), f1_score(yt2, yp2, average="macro", zero_division=0)
    label = f"C={C} maxf={cfg['max_features']} ngram={cfg['ngram_range']}"
    print(f"{label:50s} {sa:9.3f} {sf:9.3f} {ga:9.3f} {gf:9.3f}")
