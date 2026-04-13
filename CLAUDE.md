# Analytics Internship Take-Home — Voxel AI

## What this repo contains

- `safety-nonsafety/` — 99 JSON files, each a customer call with LLM-extracted use cases
- `analysis.py` — Data loading, quality audit, and nonsafety cluster analysis
- `findings.csv` — Flattened use-case table (one row per use case)
- `memo.md` — 1.5-page analyst memo with top 3 non-safety opportunities
- `SUBMISSION.md` — Notes on approach and tradeoffs

## Running the analysis

```bash
pip install pandas
python analysis.py
```

Output includes all quality audit results and cluster summaries. findings.csv is regenerated on each run.
