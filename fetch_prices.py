#!/usr/bin/env python3
"""Daily incremental OHLCV downloader for GitHub Actions.
Reads tickers.csv (column 'symbol'), writes data/<safe>.csv per ticker,
plus closes_wide.csv (adj close, last ~5y) and manifest.json."""
import csv, json, os, re, sys, time, datetime as dt
import pandas as pd
import yfinance as yf

DATA = "data"; BATCH = 40; YEARS = 5; OVERLAP_DAYS = 7
os.makedirs(DATA, exist_ok=True)

def safe(sym):            # ^GSPC -> _GSPC, GC=F -> GC_F, EURUSD=X -> EURUSD_X
    return re.sub(r"[^A-Za-z0-9.\-]", "_", sym)

def load_existing(sym):
    p = f"{DATA}/{safe(sym)}.csv"
    if os.path.exists(p):
        df = pd.read_csv(p, parse_dates=["Date"], index_col="Date")
        return p, df
    return p, None

def main():
    syms = [r["symbol"].strip() for r in csv.DictReader(open("tickers.csv")) if r["symbol"].strip()]
    today = dt.date.today()
    full_start = today - dt.timedelta(days=365 * YEARS + 10)
    # group tickers by required start date: new tickers -> full history, existing -> overlap window
    jobs = {}
    for s in syms:
        _, df = load_existing(s)
        start = full_start if df is None or df.empty else (df.index.max().date() - dt.timedelta(days=OVERLAP_DAYS))
        jobs.setdefault(start, []).append(s)
    failed, updated = [], 0
    for start, group in jobs.items():
        for i in range(0, len(group), BATCH):
            chunk = group[i:i + BATCH]
            for attempt in range(3):
                try:
                    raw = yf.download(chunk, start=start.isoformat(), end=(today + dt.timedelta(days=1)).isoformat(),
                                      interval="1d", auto_adjust=False, group_by="ticker",
                                      threads=True, progress=False)
                    break
                except Exception as e:
                    print("batch error", e, file=sys.stderr); time.sleep(30 * (attempt + 1)); raw = None
            if raw is None or raw.empty:
                failed += chunk; continue
            for s in chunk:
                try:
                    new = raw[s] if isinstance(raw.columns, pd.MultiIndex) else raw
                except KeyError:
                    failed.append(s); continue
                new = new.dropna(how="all")
                if new.empty:
                    failed.append(s); continue
                new.index = pd.to_datetime(new.index).tz_localize(None).normalize()
                new.index.name = "Date"
                p, old = load_existing(s)
                out = new if old is None else pd.concat([old[~old.index.isin(new.index)], new])
                out = out.sort_index()
                out = out[out.index >= pd.Timestamp(full_start)]       # rolling 5y window keeps repo small
                out.round(6).to_csv(p, float_format="%.10g")
                updated += 1
            time.sleep(2)                                              # be polite to Yahoo
    # wide adjusted-close matrix for fast stats in the agent sandbox
    cols = {}
    for s in syms:
        _, df = load_existing(s)
        if df is not None and "Adj Close" in df:
            cols[s] = df["Adj Close"]
    if cols:
        pd.DataFrame(cols).sort_index().to_csv("closes_wide.csv", float_format="%.10g")
    json.dump({"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "tickers": len(syms), "updated": updated, "failed": sorted(set(failed))},
              open("manifest.json", "w"), indent=1)
    print(f"updated={updated} failed={len(set(failed))}")
    # fail the job only if most downloads failed (e.g. Yahoo block), so partial days still commit
    sys.exit(1 if updated < 0.5 * len(syms) else 0)

if __name__ == "__main__":
    main()
