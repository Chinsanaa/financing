#!/usr/bin/env python3
"""One deterministic command: raw -> parse -> label -> train -> classify -> metrics.

Reproduces the full pipeline with a fixed seed. Every stage that touches
randomness is pinned (LR_HYPERPARAMS['random_state']=42, StratifiedKFold shuffle
seed, train/test split seed, label-sample seed), so two runs on the same inputs
produce identical metrics.

Stages:
  1. bootstrap.py  — parse raw exports, seed labels from merchant rules, train, classify
  2. validate.py   — schema / amount / date / duplicate checks on the parsed data
  3. retrain.py    — stratified-CV metrics report (data/reports/TRAINING_REPORT.txt)
  4. (--honest)    — GroupKFold-by-merchant evaluation (the real generalization number)

Usage:
    python run_all.py            # full deterministic pipeline
    python run_all.py --honest   # also print the honest GroupKFold evaluation

Requires your own exports in data/raw/ (gitignored). With no data present it
prints what it expected and exits cleanly (exit 0).
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

SEED = 42


def _run(desc, argv, allow_fail=False):
    print(f"\n{'='*70}\n>>> {desc}\n{'='*70}")
    rc = subprocess.run(argv, cwd=str(ROOT)).returncode
    if rc != 0 and not allow_fail:
        print(f"\nStage failed: {desc} (exit {rc})")
        sys.exit(rc)
    return rc


def main():
    ap = argparse.ArgumentParser(description="Deterministic end-to-end pipeline run.")
    ap.add_argument("--honest", action="store_true",
                    help="also run GroupKFold-by-merchant evaluation after training")
    args = ap.parse_args()

    import parse
    import pandas as pd
    import validate
    from paths import TRANSACTIONS

    print(f"Deterministic pipeline (seed={SEED}). Root: {ROOT}")

    # Guard: raw data must be present. The pipeline is meaningless without it.
    alipay, wechat, additional = parse.resolve_raw_paths(ROOT)
    if not alipay and not wechat and not additional:
        print("\nNo raw files found in data/raw/.")
        print("Expected one of: alipay.csv, raw-wechat.xlsx, bank.csv")
        print("Add your exports (gitignored) and re-run. See data/raw/README.md.")
        sys.exit(0)

    # Stage 1: parse -> label (rules) -> train -> classify (bootstrap bundles these).
    _run("Parse + label + train + classify (bootstrap)",
         [sys.executable, str(SRC / "bootstrap.py")])

    # Stage 2: validate the parsed transactions.
    print(f"\n{'='*70}\n>>> Validate parsed transactions\n{'='*70}")
    vs = validate.validate_transactions(pd.read_csv(TRANSACTIONS))
    print(validate.format_report(vs))
    if validate.has_errors(vs):
        print("Validation errors present — inspect data/raw inputs.")
        sys.exit(1)

    # Stage 3: metrics report (stratified CV — the number we currently report).
    _run("Metrics: stratified CV + per-category (TRAINING_REPORT.txt)",
         [sys.executable, str(SRC / "retrain.py")])

    # Stage 4 (optional): honest GroupKFold-by-merchant evaluation.
    if args.honest:
        _run("Honest evaluation: GroupKFold by merchant vs stratified CV",
             [sys.executable, str(ROOT / "docs" / "phase1_analysis.py")])

    print(f"\n{'='*70}\nPipeline complete (deterministic, seed={SEED}).\n{'='*70}")


if __name__ == "__main__":
    main()
