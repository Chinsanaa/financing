# Payment export files (not committed — your financial data stays local)

The product way to import data is the web app: sign in and use the
**Upload** tab, which parses these same export formats server-side.

This directory exists for local/offline work with the ML pipeline in `src/`
(e.g. running `pytest` against real files or experimenting with
`src/parse.py` directly).

## Export formats

| File | Source |
|------|--------|
| `alipay.csv` | Alipay app → 账单 (Bills) → 导出 (Export) |
| `raw-wechat.xlsx` | WeChat → 钱包 (Wallet) → 账单 (Bills) → 导出 (Export, Excel) |

## Export tips

- **Alipay**: English or Chinese column headers both work (UTF-8 or GBK).
- **WeChat**: Use the native Excel export (Chinese columns). The parser skips
  the first 17 header rows automatically.
- Only **completed expenses** are kept; refunds net against purchases and
  internal transfers (credit-card repayment, withdrawals) are excluded.
