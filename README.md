# market-data (for Global Alpha Desk)

A free GitHub Actions job downloads 5 years of daily prices for every symbol in `tickers.csv` each weekday night and commits the files. Global Alpha Desk then reads them from raw.githubusercontent.com, which its sandbox can reach.

## Setup (about 10 minutes)
1. Create a free GitHub account, then a new **public** repository named `market-data`.
2. Upload these files, keeping the folders: `fetch_prices.py`, `tickers.csv`, `.github/workflows/prices.yml`.
3. In the repository, open **Settings > Actions > General > Workflow permissions** and choose **Read and write permissions**.
4. Open the **Actions** tab, pick **daily-prices**, then **Run workflow** to do the first 5-year backfill.
5. When it finishes, check that `closes_wide.csv` and `manifest.json` exist. Then send Claude your GitHub username so it can set DATA_REPO_RAW in the runbook.

## Adding companies
Add Yahoo-format symbols to `tickers.csv` (e.g. `7203.T`, `SAN.MC`, `RELIANCE.NS`). New symbols get a 5-year backfill on the next run. Up to about 1,000 symbols is fine.

## Notes
- The data comes from Yahoo Finance via yfinance and is meant for personal research use. Because the repository is public, anyone can see the files.
- If runs start failing because Yahoo rate-limits the runner, the workflow already installs `curl_cffi`. Upgrading `yfinance` usually fixes it.
- GitHub turns off schedules after 60 days with no repository activity. The daily commits count as activity.
