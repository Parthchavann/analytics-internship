# analysis.py — Voxel AI Non-Safety Opportunities Analysis
# Parth Chavan | April 2026
#
# Manual inspection notes (from reading 8 files before scripting):
# - Total files: 99
# - Top-level fields: meeting_title, start_time, extraction
#   (no "meeting_metadata" key — just flat title + timestamp at root)
# - extraction contains: safety_use_cases, nonsafety_use_cases (both lists)
# - Each use case has: label, description, evidence (list of {quote, speaker, timestamp})
# - Typical use_case label: short noun phrase, e.g. "PIT-to-pedestrian proximity monitoring"
#   or "Video footage retrieval" — generally specific, not generic
# - Evidence: full sentence quotes pulled from call transcripts — usually 1-4 quotes per use case
#   Some are thin (single fragment quote), none were empty in the 8 inspected
# - No malformed or empty files found in manual sample
# - Some safety use cases (e.g. "safety trend review") could plausibly appear as nonsafety;
#   cross-bucket bleed is possible and worth checking
# - Generic/admin labels present: "follow-up", "next steps" type labels do appear occasionally

import json
import os
import re
import sys
import pandas as pd
from collections import Counter

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = "safety-nonsafety"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Load all JSON files
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("SECTION 1: Loading JSON files")
print("=" * 70)

records = []
errors = []

for fname in os.listdir(DATA_DIR):
    if not fname.endswith(".json"):
        continue
    fpath = os.path.join(DATA_DIR, fname)
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        records.append((fname, data))
    except Exception as e:
        errors.append((fname, str(e)))

print(f"Files loaded: {len(records)}")
print(f"Parse errors: {len(errors)}")
for fname, err in errors:
    print(f"  ERROR {fname}: {err}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Flatten into tidy DataFrame
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 2: Building DataFrame")
print("=" * 70)

rows = []
for fname, data in records:
    meeting_title = data.get("meeting_title", "")
    start_time = data.get("start_time", "")
    extraction = data.get("extraction", {})

    for bucket, key in [("safety", "safety_use_cases"), ("nonsafety", "nonsafety_use_cases")]:
        use_cases = extraction.get(key, [])
        if not isinstance(use_cases, list):
            continue
        for uc in use_cases:
            label = uc.get("label", "").strip()
            description = uc.get("description", "").strip()
            evidence_list = uc.get("evidence", [])
            quotes = [e.get("quote", "").strip() for e in evidence_list if isinstance(e, dict)]
            evidence_joined = " | ".join(q for q in quotes if q)
            n_evidence = len([q for q in quotes if q])
            rows.append({
                "file": fname,
                "meeting_title": meeting_title,
                "start_time": start_time,
                "bucket": bucket,
                "use_case": label,
                "description": description,
                "evidence_joined": evidence_joined,
                "n_evidence": n_evidence,
            })

df = pd.DataFrame(rows)
df.to_csv("findings.csv", index=False)

print(f"Total rows (use cases): {len(df)}")
print(f"Safety rows:    {len(df[df.bucket == 'safety'])}")
print(f"Nonsafety rows: {len(df[df.bucket == 'nonsafety'])}")
print(f"Unique files represented: {df.file.nunique()}")
print("Saved to findings.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Quality Audit
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 3: Quality Audit")
print("=" * 70)

# Q1: Use cases with zero evidence
q1 = df[df.n_evidence == 0]
print(f"\nQ1 — Zero-evidence use cases (unverifiable): {len(q1)}")
if len(q1) > 0:
    print(q1[["file", "bucket", "use_case"]].to_string(index=False))

# Q2: Exact duplicate use_case strings across files
label_counts = df.groupby("use_case")["file"].nunique()
dupes = label_counts[label_counts > 1].sort_values(ascending=False)
print(f"\nQ2 — Use case labels appearing in 2+ files: {len(dupes)}")
print("Top 10 duplicated labels:")
print(dupes.head(10).to_string())

# Q3: Cross-bucket bleed — same label in both safety and nonsafety
safety_labels = set(df[df.bucket == "safety"]["use_case"].str.lower().str.strip())
nonsafety_labels = set(df[df.bucket == "nonsafety"]["use_case"].str.lower().str.strip())
crossbleed = safety_labels & nonsafety_labels
print(f"\nQ3 — Labels appearing in BOTH safety and nonsafety buckets: {len(crossbleed)}")
for l in sorted(crossbleed):
    print(f"  '{l}'")

# Q4: Generic/admin labels
generic_pattern = re.compile(
    r"\b(follow[\s-]?up|schedule|next steps|action items?|touch base|"
    r"check[\s-]?in|agenda|demo request|intro|overview|introduction)\b",
    re.IGNORECASE,
)
q4 = df[df.use_case.str.contains(generic_pattern, na=False)]
print(f"\nQ4 — Generic/admin labels (not real product signals): {len(q4)}")
if len(q4) > 0:
    print(q4[["file", "bucket", "use_case"]].to_string(index=False))

# Q5: Label overstatement — 7+ word label but thin evidence (<50 chars)
df["word_count"] = df.use_case.apply(lambda x: len(str(x).split()))
q5 = df[(df.word_count >= 7) & (df.evidence_joined.str.len() < 50)]
print(f"\nQ5 — Long label (7+ words) with thin evidence (<50 chars): {len(q5)}")
if len(q5) > 0:
    print(q5[["file", "bucket", "use_case", "evidence_joined"]].to_string(index=False))

# Q6: Files with outlier use case counts (<=1 or very high)
file_uc_counts = df.groupby("file").size().sort_values()
low_count = file_uc_counts[file_uc_counts <= 1]
high_count = file_uc_counts[file_uc_counts >= file_uc_counts.quantile(0.95)]
print(f"\nQ6 — Files with <=1 use case: {len(low_count)}")
print(low_count.to_string())
print(f"\nQ6 — Files with use case counts >= 95th percentile ({file_uc_counts.quantile(0.95):.0f}):")
print(high_count.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Normalize nonsafety use cases into clusters
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 4: Nonsafety Cluster Analysis")
print("=" * 70)

# Clean nonsafety rows
ns = df[
    (df.bucket == "nonsafety") &
    (df.n_evidence > 0) &
    (df.use_case.str.strip() != "") &
    (~df.use_case.str.contains(generic_pattern, na=False))
].copy()

print(f"\nCleaned nonsafety rows (non-generic, has evidence): {len(ns)}")

# Top 30 most frequent use_case strings to understand patterns
print("\nTop 30 most frequent nonsafety use_case labels:")
top30 = ns["use_case"].value_counts().head(30)
print(top30.to_string())


def assign_cluster(label: str) -> str:
    """
    Keyword-based cluster assignment for nonsafety use cases.
    Order matters — first match wins.
    """
    l = label.lower()

    # Insurance / liability / claims / exoneration
    if any(k in l for k in ["insurance", "claim", "liability", "incident report",
                              "workers comp", "workers' comp", "osha", "recordable",
                              "near miss", "incident log", "case management",
                              "exonerat", "litigation", "legal defense",
                              "lower workers"]):
        return "Insurance & Claims Reduction"

    # Action tracking / accountability workflow (assign, track, close the loop)
    if any(k in l for k in ["assign and track", "assign incidents", "action tracking",
                              "corrective action", "track actions", "action workflow",
                              "accountability", "reminders for", "overdue action",
                              "past-due action", "track intervention",
                              "track and find", "track corrective",
                              "close the loop", "action management",
                              "track follow", "actions with owner"]):
        return "Action Tracking & Accountability"

    # Operational efficiency / productivity / throughput / dwell / door duration
    if any(k in l for k in ["throughput", "productivity", "efficiency", "output",
                              "bottleneck", "utilization", "dwell", "idle",
                              "operational", "process improvement",
                              "staffing", "labor", "headcount", "overtime",
                              "cycle time", "downtime", "parking duration",
                              "door duration", "dock door", "door open",
                              "door monitor", "door tracking", "turn-time",
                              "turnaround time", "detention",
                              "trailer", "vehicle idling", "parking monitor",
                              "aisle flow", "charger parking", "cold storage door",
                              "cooler", "freezer door", "machine downtime",
                              "machine shutdown", "reduce time spent",
                              "automate camera monitoring", "manual observation"]):
        return "Operational Efficiency & Labor"

    # Video footage retrieval / investigation / evidence
    if any(k in l for k in ["footage retrieval", "video retrieval", "video access",
                              "clip retrieval", "video review", "playback",
                              "video audit", "surveillance", "camera access",
                              "footage", "video evidence", "video footage",
                              "incident investigation", "accelerate incident",
                              "embed incident video", "skeleton overlay"]):
        return "Video Evidence & Investigations"

    # Training / coaching / behavior change / culture
    if any(k in l for k in ["training", "coaching", "behavior", "onboard",
                              "educate", "awareness", "culture", "reinforce",
                              "learning", "teach", "demonstration",
                              "change management", "storytelling", "retention"]):
        return "Training & Behavior Coaching"

    # Reporting / analytics / dashboards / heatmaps / exports
    if any(k in l for k in ["report", "dashboard", "analytic", "metric",
                              "kpi", "data export", "trend", "scorecard",
                              "leaderboard", "benchmark", "summary",
                              "visibility", "audit trail", "documentation",
                              "heatmap", "heat map", "email summaries",
                              "email summary", "historical data",
                              "platform adoption", "usage analytic",
                              "snapshot", "data delivery", "gamification",
                              "export", "presentation deck", "boards"]):
        return "Reporting & Analytics"

    # Security / theft / loss prevention / after-hours / restricted access
    if any(k in l for k in ["theft", "shrink", "loss prevention", "security",
                              "unauthorized", "intrusion", "access control",
                              "shoplifting", "asset protection",
                              "after-hours", "after hours", "restricted access",
                              "restricted area", "no-pedestrian zone",
                              "no pedestrian", "no-parking zone",
                              "no-idling", "no-standing", "no-traffic"]):
        return "Security & Loss Prevention"

    # Product / asset damage detection
    if any(k in l for k in ["product damage", "asset damage", "infrastructure damage",
                              "damage detection", "rack damage", "collision damage",
                              "agv", "laser-guided", "damage tracking",
                              "damage prevention", "damage monitor",
                              "product condition", "sensitive product"]):
        return "Product & Asset Damage Detection"

    # Food safety / specialized compliance (PPE food context)
    if any(k in l for k in ["food safety", "food hygiene", "hair net", "beard net",
                              "controlled-environment", "cold storage compliance",
                              "sanitation"]):
        return "Food Safety & Compliance"

    # Vendor / contractor / visitor management
    if any(k in l for k in ["vendor", "contractor", "visitor", "third party",
                              "third-party", "subcontractor", "supplier",
                              "carrier", "driver compliance", "yard gate",
                              "customs"]):
        return "Vendor & Contractor Management"

    # Facilities / maintenance / compliance audit
    if any(k in l for k in ["facility", "maintenance", "housekeeping",
                              "cleanliness", "5s", "compliance audit",
                              "inspection", "audit", "blocked", "obstruct",
                              "fire extinguisher", "emergency exit",
                              "energy saving"]):
        return "Facilities & Compliance Auditing"

    # Expansion / multi-site / scale / adoption
    if any(k in l for k in ["expand", "scale", "multi-site", "multi site",
                              "roll out", "rollout", "pilot", "deployment",
                              "additional site", "new site", "enterprise",
                              "adoption", "engagement", "cross-functional",
                              "stakeholder alignment", "platform engagement",
                              "broaden", "potential expansion"]):
        return "Multi-Site Expansion & Adoption"

    # Integration / infrastructure / camera setup
    if any(k in l for k in ["integrat", "api", "camera infrastructure",
                              "nvr", "vms", "legacy camera", "iot",
                              "camera coverage", "rescop", "re-scop",
                              "camera zone", "blind spot"]):
        return "Platform Integration & Infrastructure"

    return "Other"


ns["cluster"] = ns["use_case"].apply(assign_cluster)

# Cluster summary
cluster_summary = (
    ns.groupby("cluster")
    .agg(
        n_mentions=("use_case", "count"),
        n_calls=("file", "nunique"),
    )
    .sort_values("n_calls", ascending=False)
    .reset_index()
)

print("\nCluster summary (sorted by n_calls — breadth of signal):")
print(cluster_summary.to_string(index=False))

other_pct = len(ns[ns.cluster == "Other"]) / len(ns) * 100
print(f"\n'Other' bucket: {len(ns[ns.cluster == 'Other'])} rows ({other_pct:.1f}%)")
print("\n'Other' labels sample:")
print(ns[ns.cluster == "Other"]["use_case"].value_counts().head(15).to_string())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Evidence for top 3 clusters
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 5: Evidence for Top 3 Clusters")
print("=" * 70)

top3_clusters = cluster_summary[cluster_summary["cluster"] != "Other"].head(3)["cluster"].tolist()

for cluster_name in top3_clusters:
    subset = ns[ns.cluster == cluster_name]
    n_mentions = len(subset)
    n_calls = subset["file"].nunique()
    top_labels = subset["use_case"].value_counts().head(5)

    print(f"\n{'─'*60}")
    print(f"CLUSTER: {cluster_name}")
    print(f"  Mentions: {n_mentions} | Calls: {n_calls}")
    print("  Top use case labels:")
    for label, cnt in top_labels.items():
        print(f"    ({cnt}x) {label}")

    # 3 sample evidence quotes (up to 250 chars each)
    sample_evidence = []
    for _, row in subset.iterrows():
        for quote in row["evidence_joined"].split(" | "):
            quote = quote.strip()
            if quote and len(quote) > 20:
                sample_evidence.append(quote[:250])
            if len(sample_evidence) >= 3:
                break
        if len(sample_evidence) >= 3:
            break

    print("  Sample evidence:")
    for i, q in enumerate(sample_evidence, 1):
        print(f"    [{i}] \"{q}\"")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Summary stats for memo
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 6: Summary Stats")
print("=" * 70)

total_calls = df["file"].nunique()
total_rows = len(df)
safety_count = len(df[df.bucket == "safety"])
nonsafety_count = len(df[df.bucket == "nonsafety"])
cleaned_ns_count = len(ns)

print(f"Total calls (files): {total_calls}")
print(f"Total use case rows: {total_rows}")
print(f"Safety rows:         {safety_count}")
print(f"Nonsafety rows:      {nonsafety_count}")
print(f"Cleaned nonsafety:   {cleaned_ns_count}")
print(f"")
print(f"Q1 Zero-evidence use cases:           {len(q1)}")
print(f"Q2 Labels in 2+ files (exact dupes):  {len(dupes)}")
print(f"Q3 Cross-bucket bleed labels:         {len(crossbleed)}")
print(f"Q4 Generic/admin labels:              {len(q4)}")
print(f"Q5 Long label + thin evidence:        {len(q5)}")
print(f"Q6 Files with <=1 use case:           {len(low_count)}")
