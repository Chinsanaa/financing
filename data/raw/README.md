# Payment export files (not committed — your financial data stays local)

Drop your exports here, then run:

```bash
python src/bootstrap.py
```

## Required file names

| File | Source |
|------|--------|
| `alipay.csv` | Alipay app → 账单 → 导出 |
| `raw-wechat.xlsx` | WeChat → 钱包 → 账单 → 导出 (Excel) |

Alternative names also work: `alipay_expenses.csv`, `wechat.xlsx`, `wechat.csv`.

## Optional: bank / credit card

- `bank.csv` or `credit_card.csv` — auto-detected if columns match common Chinese/English headers
- Or copy `source_config.example.json` → `source_config.json` and map your bank's column names

## Export tips

- **Alipay**: English or Chinese column headers both work (UTF-8 or GBK).
- **WeChat**: Use the native Excel export (Chinese columns). The parser skips the first 17 header rows automatically.
- Only **completed expenses** are kept; refunds and transfers are filtered out.

See the main README **New User Setup** section for the full workflow.
