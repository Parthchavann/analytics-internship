# analysis.py — Voxel AI Non-Safety Opportunities Analysis (v2)
# Parth Chavan | April 2026
#
# Manual inspection notes (from reading 8 files before scripting):
# - Total files: 99
# - Top-level fields: meeting_title, start_time, extraction
#   (no "meeting_metadata" key — flat title + timestamp at root)
# - extraction contains: safety_use_cases, nonsafety_use_cases (both lists)
# - Each use case: label, description, evidence [{quote, speaker, timestamp}]
# - Typical label: specific noun phrase e.g. "PIT-to-pedestrian proximity monitoring"
# - Evidence: full sentence quotes, 1-4 per use case; some very short fragments
# - No malformed/empty files in sample; cross-bucket bleed apparent on inspection
# - Generic/admin labels present but minority (scheduling, follow-up type)
# - Speaker emails: voxelai.com = Voxel rep; other domains = customer
#   This matters — Voxel-prompted use cases are weaker signal than customer-initiated ones

import json
import os
import re
import sys
from itertools import combinations
from collections import defaultdict

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = "safety-nonsafety"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

SAFETY_CORE_TERMS = [
    "safety", "injury", "hazard", "ergonomic", "ppe", "near-miss", "near miss",
    "fire", "evacuation", "collision", "osha", "recordable", "workers comp",
    "workers' comp", "slip", "fall", "trip",
]

ADMIN_COMMERCIAL_TERMS = [
    "contract renewal", "customer success support", "responsive customer support",
    "ongoing partnership", "cost-sensitive vendor", "vendor evaluation",
    "longer-term commercial", "language clarification", "business case support",
    "getting sites onto the same schedule", "timing follow-up around internal",
    "per-user language localization",
]

# Stopwords for Jaccard tokenization
STOPWORDS = {
    "monitoring", "tracking", "management", "safety", "use", "case", "and",
    "or", "the", "a", "an", "for", "with", "via", "using", "of", "in", "at",
    "to", "from", "on", "by", "based", "related", "across", "within",
}

# Theme clusters — order matters (first match wins)
THEMES = {
    "Workflow & Action Management": [
        "assign and track", "assign incidents", "track action", "track corrective",
        "corrective action", "action workflow", "action management", "accountability",
        "reminders for", "overdue action", "past-due", "due date",
        "close the loop", "action tracking", "action board", "voxel action",
        "platform action", "role-based access", "cross-shift", "impact marker",
        "track follow", "track and find", "track intervention",
        "voxel-assigned action", "action with owner", "ownership",
        "incident and track", "assign action", "assign incident",
        "track safety action", "loop on safety",
    ],
    "Reporting & Analytics": [
        "report", "dashboard", "analytic", "metric", "kpi", "data export",
        "trend", "scorecard", "leaderboard", "benchmark", "summary",
        "visibility", "documentation", "heatmap", "heat map",
        "email summar", "historical data", "platform adoption", "usage analytic",
        "snapshot", "data delivery", "gamification", "export", "presentation deck",
        "boards", "multi-site analytic", "cross-site analytic", "executive",
        "interactive report", "weekly report", "subscription",
    ],
    "Operational Efficiency & Labor": [
        "throughput", "productivity", "efficiency", "output", "bottleneck",
        "utilization", "dwell", "idle", "operational", "process improvement",
        "staffing", "labor", "headcount", "overtime", "cycle time", "downtime",
        "parking duration", "door duration", "dock door", "door open",
        "door monitor", "door tracking", "turn-time", "turnaround time",
        "detention", "trailer", "vehicle idling", "parking monitor",
        "aisle flow", "charger parking", "cold storage door", "cooler",
        "freezer door", "machine shutdown", "reduce time spent",
        "automate camera monitoring", "manual observation", "conveyor",
        "congestion", "flow pattern",
    ],
    "Security & Loss Prevention": [
        "theft", "shrink", "loss prevention", "security", "unauthorized",
        "intrusion", "access control", "shoplifting", "asset protection",
        "after-hours", "after hours", "restricted access", "restricted area",
        "no-pedestrian zone", "no pedestrian", "no-parking zone",
        "no-idling", "no-standing", "no-traffic",
    ],
    "Video Evidence & Investigations": [
        "footage retrieval", "video retrieval", "video access", "clip retrieval",
        "video review", "playback", "video audit", "camera access", "footage",
        "video evidence", "video footage", "incident investigation",
        "accelerate incident", "embed incident video", "skeleton overlay",
        "exonerat", "timestamp",
    ],
    "Training & Behavior Coaching": [
        "training", "coaching", "behavior", "onboard", "educate", "awareness",
        "culture", "reinforce", "learning", "teach", "demonstration",
        "change management", "storytelling", "retention", "toolbox talk",
        "bookmarked clip",
    ],
    "Insurance & Claims Reduction": [
        "insurance", "liability", "incident report", "workers comp",
        "workers' comp", "recordable", "near miss", "case management",
        "exonerat", "litigation", "lower workers", "reduce injury cost",
        "injury cost", "claim",
    ],
    "Product & Asset Damage Detection": [
        "product damage", "asset damage", "infrastructure damage",
        "damage detection", "rack damage", "collision damage", "agv",
        "laser-guided", "damage tracking", "damage prevention", "damage monitor",
        "product condition", "sensitive product", "equipment damage",
    ],
    "Food Safety & Compliance": [
        "food safety", "food hygiene", "hair net", "beard net",
        "controlled-environment", "sanitation",
    ],
    "Vendor & Contractor Management": [
        "vendor", "contractor", "visitor", "third party", "third-party",
        "subcontractor", "supplier", "carrier", "driver compliance",
        "yard gate", "customs",
    ],
    "Facilities & Compliance Auditing": [
        "facility", "maintenance", "housekeeping", "cleanliness", "5s",
        "compliance audit", "inspection", "audit", "blocked", "obstruct",
        "fire extinguisher", "emergency exit", "energy saving",
    ],
    "Multi-Site Expansion & Adoption": [
        "expand", "scale", "multi-site", "multi site", "roll out", "rollout",
        "pilot", "additional site", "new site", "enterprise", "adoption",
        "cross-functional", "platform engagement", "broaden",
        "potential expansion", "deployment",
    ],
    "Platform Integration & Infrastructure": [
        "integrat", "api", "camera infrastructure", "nvr", "vms",
        "legacy camera", "iot", "camera coverage", "rescop", "re-scop",
        "camera zone", "blind spot", "upgrade",
    ],
}

# Generic/admin labels — very conservative list, specific phrases only
GENERIC_PHRASES = [
    "getting sites onto the same schedule",
    "timing follow-up around internal planning",
    "touch base",
    "next steps",
    "check-in",
    "agenda",
    "demo request",
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def is_generic(label: str) -> bool:
    """Return True only for clearly administrative/scheduling labels."""
    l = label.lower().strip()
    return any(phrase in l for phrase in GENERIC_PHRASES)


def is_voxel_speaker(speaker: str) -> bool:
    return "voxelai.com" in speaker.lower()


def assign_theme(label: str) -> str:
    l = label.lower()
    for theme, keywords in THEMES.items():
        if any(k in l for k in keywords):
            return theme
    return "Other"


def tokenize(label: str) -> set:
    tokens = re.findall(r"\b[a-z]+\b", label.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def jaccard(a: str, b: str) -> float:
    sa, sb = tokenize(a), tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Load JSON files
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("SECTION 1: Loading JSON files")
print("=" * 70)

records = []
errors = []

for fname in sorted(os.listdir(DATA_DIR)):
    if not fname.endswith(".json"):
        continue
    fpath = os.path.join(DATA_DIR, fname)
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        records.append((fname, data))
    except Exception as e:
        errors.append((fname, str(e)))

print(f"Files loaded:  {len(records)}")
print(f"Parse errors:  {len(errors)}")
for fname, err in errors:
    print(f"  ERROR {fname}: {err}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Flatten into tidy DataFrame
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 2: Flattening to DataFrame")
print("=" * 70)

rows = []
for fname, data in records:
    meeting_title = data.get("meeting_title", "")
    start_time    = data.get("start_time", "")
    try:
        year = int(start_time[:4]) if start_time else None
    except Exception:
        year = None

    extraction = data.get("extraction", {})
    for bucket, key in [("safety", "safety_use_cases"), ("nonsafety", "nonsafety_use_cases")]:
        for uc in extraction.get(key, []):
            label       = uc.get("label", "").strip()
            description = uc.get("description", "").strip()
            ev_list     = uc.get("evidence", [])

            quotes    = []
            speakers  = []
            has_customer_quote = False

            for e in ev_list:
                if not isinstance(e, dict):
                    continue
                q = e.get("quote", "").strip()
                s = e.get("speaker", "").strip()
                if q:
                    quotes.append(q)
                    speakers.append(s)
                    if not is_voxel_speaker(s):
                        has_customer_quote = True

            n_evidence        = len(quotes)
            evidence_joined   = " | ".join(quotes)
            n_voxel_quotes    = sum(1 for s in speakers if is_voxel_speaker(s))
            n_customer_quotes = n_evidence - n_voxel_quotes
            min_quote_len     = min((len(q) for q in quotes), default=0)
            avg_quote_len     = sum(len(q) for q in quotes) / n_evidence if n_evidence else 0

            rows.append({
                "file":               fname,
                "meeting_title":      meeting_title,
                "year":               year,
                "bucket":             bucket,
                "use_case":           label,
                "description":        description,
                "evidence_joined":    evidence_joined,
                "n_evidence":         n_evidence,
                "n_customer_quotes":  n_customer_quotes,
                "n_voxel_quotes":     n_voxel_quotes,
                "has_customer_quote": has_customer_quote,
                "min_quote_len":      min_quote_len,
                "avg_quote_len":      round(avg_quote_len, 1),
            })

df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUTPUT_DIR, "flattened_use_cases.csv"), index=False)

total_calls = df["file"].nunique()
print(f"Total rows:          {len(df)}")
print(f"Safety rows:         {len(df[df.bucket == 'safety'])}")
print(f"Nonsafety rows:      {len(df[df.bucket == 'nonsafety'])}")
print(f"Unique files:        {total_calls}")
print(f"Saved → outputs/flattened_use_cases.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Quality Audit — 7 checks
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 3: Quality Audit")
print("=" * 70)

ns_all = df[df.bucket == "nonsafety"].copy()

# Q1: Weak evidence — any use case where ALL quotes are under 35 chars
q1 = ns_all[ns_all.apply(
    lambda r: r["n_evidence"] > 0 and r["min_quote_len"] < 35, axis=1
)]
print(f"\nQ1 — Weak evidence (shortest quote < 35 chars): {len(q1)}")
q1_out = q1[["file", "meeting_title", "use_case", "min_quote_len", "evidence_joined"]].copy()
q1_out.to_csv(os.path.join(OUTPUT_DIR, "weak_evidence.csv"), index=False)
print(f"     Saved → outputs/weak_evidence.csv")
print("     Sample:")
for _, r in q1_out.head(4).iterrows():
    print(f"       [{r['min_quote_len']}c] \"{r['use_case']}\"")

# Q2: Exact duplicate label strings (same text across 2+ files)
label_file_counts = df.groupby("use_case")["file"].nunique()
q2 = label_file_counts[label_file_counts > 1].sort_values(ascending=False)
print(f"\nQ2 — Exact-duplicate labels (in 2+ files): {len(q2)}")
print("     Top 10:")
print(q2.head(10).to_string())

# Q3: Near-duplicate labels via Jaccard similarity (threshold 0.45)
ns_labels = ns_all["use_case"].dropna().unique().tolist()
near_dupes = []
for a, b in combinations(ns_labels, 2):
    sim = jaccard(a, b)
    if sim >= 0.45 and a.lower().strip() != b.lower().strip():
        near_dupes.append({"label_a": a, "label_b": b, "jaccard": round(sim, 3)})

q3_df = pd.DataFrame(near_dupes).sort_values("jaccard", ascending=False) if near_dupes else pd.DataFrame()
print(f"\nQ3 — Near-duplicate labels (Jaccard ≥ 0.45): {len(q3_df)}")
if not q3_df.empty:
    q3_df.to_csv(os.path.join(OUTPUT_DIR, "near_duplicates.csv"), index=False)
    print(f"     Saved → outputs/near_duplicates.csv")
    print("     Top 5 pairs:")
    for _, r in q3_df.head(5).iterrows():
        print(f"       [{r['jaccard']}] \"{r['label_a']}\"  ≈  \"{r['label_b']}\"")

# Q4: Cross-bucket exact label overlap per call
crossbleed_rows = []
for fname, grp in df.groupby("file"):
    safety_labels    = set(grp[grp.bucket == "safety"]["use_case"].str.lower().str.strip())
    nonsafety_labels = set(grp[grp.bucket == "nonsafety"]["use_case"].str.lower().str.strip())
    overlap          = safety_labels & nonsafety_labels
    for lbl in overlap:
        crossbleed_rows.append({"file": fname, "meeting_title": grp["meeting_title"].iloc[0], "label": lbl})

q4_df = pd.DataFrame(crossbleed_rows)
q4_calls = q4_df["file"].nunique() if not q4_df.empty else 0
print(f"\nQ4 — Cross-bucket exact overlap: {len(q4_df)} instances across {q4_calls} calls")
if not q4_df.empty:
    q4_df.to_csv(os.path.join(OUTPUT_DIR, "cross_bucket_overlap.csv"), index=False)
    print(f"     Saved → outputs/cross_bucket_overlap.csv")

# Q5: Safety-core terms inside nonsafety labels
def has_safety_core(label: str) -> bool:
    l = label.lower()
    return any(re.search(r"\b" + re.escape(t) + r"\b", l) for t in SAFETY_CORE_TERMS)

q5 = ns_all[ns_all["use_case"].apply(has_safety_core)]
print(f"\nQ5 — Safety-core terms in nonsafety labels: {len(q5)}")
q5_out = q5[["file", "meeting_title", "use_case"]].copy()
q5_out.to_csv(os.path.join(OUTPUT_DIR, "safety_core_in_nonsafety.csv"), index=False)
print(f"     Saved → outputs/safety_core_in_nonsafety.csv")
print("     Sample:")
for lbl in q5["use_case"].head(5).tolist():
    print(f"       \"{lbl}\"")

# Q6: Admin/commercial noise in nonsafety
def is_admin_noise(label: str, description: str) -> bool:
    combined = (label + " " + description).lower()
    return any(phrase in combined for phrase in ADMIN_COMMERCIAL_TERMS)

q6 = ns_all[ns_all.apply(lambda r: is_admin_noise(r["use_case"], r["description"]), axis=1)]
print(f"\nQ6 — Admin/commercial noise in nonsafety: {len(q6)}")
q6_out = q6[["file", "meeting_title", "use_case"]].copy()
q6_out.to_csv(os.path.join(OUTPUT_DIR, "admin_noise.csv"), index=False)
print(f"     Saved → outputs/admin_noise.csv")
for lbl in q6["use_case"].tolist():
    print(f"       \"{lbl}\"")

# Q7: Voxel-rep-only evidence (no customer quote — weaker signal)
q7 = ns_all[(ns_all.n_evidence > 0) & (ns_all.has_customer_quote == False)]
print(f"\nQ7 — Nonsafety use cases with NO customer quotes (Voxel-rep-only evidence): {len(q7)}")
q7_out = q7[["file", "use_case", "n_voxel_quotes", "evidence_joined"]].copy()
q7_out.to_csv(os.path.join(OUTPUT_DIR, "voxel_prompted_only.csv"), index=False)
print(f"     Saved → outputs/voxel_prompted_only.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Speaker Attribution Analysis
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 4: Speaker Attribution Analysis")
print("=" * 70)

ns_with_ev = ns_all[ns_all.n_evidence > 0]
total_ns_uc = len(ns_with_ev)
customer_initiated = len(ns_with_ev[ns_with_ev.has_customer_quote == True])
voxel_only         = len(ns_with_ev[ns_with_ev.has_customer_quote == False])

print(f"Nonsafety use cases with evidence: {total_ns_uc}")
print(f"  Has at least one customer quote: {customer_initiated} ({customer_initiated/total_ns_uc*100:.1f}%)")
print(f"  Voxel-rep quotes only:           {voxel_only} ({voxel_only/total_ns_uc*100:.1f}%)")
print(f"\n  Voxel-rep-only use cases are weaker signals — the customer did not")
print(f"  explicitly raise the topic; a Voxel rep described it for them.")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Cluster Nonsafety Use Cases
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 5: Nonsafety Cluster Analysis")
print("=" * 70)

# Clean: non-generic, has evidence, non-empty label
ns_clean = ns_all[
    (ns_all.n_evidence > 0) &
    (ns_all.use_case.str.strip() != "") &
    (~ns_all.use_case.apply(is_generic))
].copy()

print(f"\nCleaned nonsafety rows (has evidence, non-generic): {len(ns_clean)}")

# Top 30 most frequent labels (raw, before clustering)
print("\nTop 30 nonsafety labels by frequency:")
top30 = ns_clean["use_case"].value_counts().head(30)
print(top30.to_string())

ns_clean["theme"] = ns_clean["use_case"].apply(assign_theme)

theme_summary = (
    ns_clean.groupby("theme")
    .agg(
        n_mentions=("use_case", "count"),
        n_calls=("file", "nunique"),
        pct_of_calls=("file", lambda x: round(x.nunique() / total_calls * 100, 1)),
    )
    .sort_values("n_calls", ascending=False)
    .reset_index()
)

print("\nTheme summary (sorted by n_calls):")
print(theme_summary.to_string(index=False))
theme_summary.to_csv(os.path.join(OUTPUT_DIR, "theme_summary.csv"), index=False)
print(f"\nSaved → outputs/theme_summary.csv")

other_pct = len(ns_clean[ns_clean.theme == "Other"]) / len(ns_clean) * 100
print(f"\n'Other' bucket: {len(ns_clean[ns_clean.theme == 'Other'])} rows ({other_pct:.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Temporal Analysis — clusters by year
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 6: Temporal Analysis (call year vs theme)")
print("=" * 70)

ns_year = ns_clean[ns_clean.year.notna()].copy()
ns_year["year"] = ns_year["year"].astype(int)

top_themes = theme_summary[theme_summary.theme != "Other"].head(4)["theme"].tolist()
temporal = (
    ns_year[ns_year.theme.isin(top_themes)]
    .groupby(["year", "theme"])["file"]
    .nunique()
    .unstack(fill_value=0)
    .sort_index()
)

print("\nDistinct calls per theme by year:")
print(temporal.to_string())
temporal.to_csv(os.path.join(OUTPUT_DIR, "temporal_analysis.csv"))
print(f"\nSaved → outputs/temporal_analysis.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: Evidence for Top 3 Themes
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 7: Evidence for Top 3 Themes")
print("=" * 70)

top3 = theme_summary[theme_summary.theme != "Other"].head(3)["theme"].tolist()

for theme_name in top3:
    subset = ns_clean[ns_clean.theme == theme_name]
    n_mentions = len(subset)
    n_calls    = subset["file"].nunique()
    pct        = round(n_calls / total_calls * 100, 1)
    top_labels = subset["use_case"].value_counts().head(5)

    # Prefer customer quotes; fall back to any quote
    customer_quotes = []
    all_quotes      = []
    for _, row in subset.iterrows():
        for q in row["evidence_joined"].split(" | "):
            q = q.strip()
            if len(q) > 30:
                all_quotes.append(q[:260])
        for q, has_cust in zip(
            row["evidence_joined"].split(" | "),
            [row["has_customer_quote"]] * row["n_evidence"]
        ):
            q = q.strip()
            if len(q) > 30 and row["has_customer_quote"] and row["n_customer_quotes"] > 0:
                customer_quotes.append(q[:260])

    sample_quotes = (customer_quotes[:3] if len(customer_quotes) >= 3 else all_quotes[:3])

    print(f"\n{'─'*60}")
    print(f"THEME: {theme_name}")
    print(f"  Calls: {n_calls} ({pct}% of all calls) | Mentions: {n_mentions}")
    voxel_only_in_theme = len(subset[subset.has_customer_quote == False])
    print(f"  Voxel-rep-only evidence: {voxel_only_in_theme}/{n_mentions} use cases")
    print("  Top labels:")
    for lbl, cnt in top_labels.items():
        print(f"    ({cnt}x) {lbl}")
    print("  Sample evidence:")
    for i, q in enumerate(sample_quotes, 1):
        print(f"    [{i}] \"{q}\"")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: Summary Stats
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 8: Summary Stats")
print("=" * 70)

print(f"Total calls (files):          {total_calls}")
print(f"Total use case rows:          {len(df)}")
print(f"Safety rows:                  {len(df[df.bucket == 'safety'])}")
print(f"Nonsafety rows:               {len(df[df.bucket == 'nonsafety'])}")
print(f"Cleaned nonsafety rows:       {len(ns_clean)}")
print(f"")
print(f"Q1 Weak evidence (<35c quote):          {len(q1)}")
print(f"Q2 Exact duplicate labels (2+ files):   {len(q2)}")
print(f"Q3 Near-duplicate pairs (Jaccard≥0.45): {len(q3_df)}")
print(f"Q4 Cross-bucket overlap (calls):        {q4_calls}")
print(f"Q5 Safety-core in nonsafety labels:     {len(q5)}")
print(f"Q6 Admin/commercial noise:              {len(q6)}")
print(f"Q7 Voxel-rep-only evidence:             {len(q7)}")
print(f"")
print(f"Speaker attribution (nonsafety, has evidence):")
print(f"  Customer-initiated:  {customer_initiated} ({customer_initiated/total_ns_uc*100:.1f}%)")
print(f"  Voxel-prompted only: {voxel_only} ({voxel_only/total_ns_uc*100:.1f}%)")
print(f"")
print(f"Outputs saved to: {OUTPUT_DIR}/")
print(f"  flattened_use_cases.csv")
print(f"  theme_summary.csv")
print(f"  cross_bucket_overlap.csv")
print(f"  weak_evidence.csv")
print(f"  near_duplicates.csv")
print(f"  safety_core_in_nonsafety.csv")
print(f"  admin_noise.csv")
print(f"  voxel_prompted_only.csv")
print(f"  temporal_analysis.csv")
