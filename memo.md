# Non-Safety Opportunities in Voxel Customer Calls
**Parth Chavan | April 2026**

---

## Dataset & Approach

99 JSON files, each representing a customer call, were analyzed. Each file contained LLM-extracted use cases tagged as either "safety" or "nonsafety." Before writing any code, I read 8 files manually to understand the extraction format, label style, and evidence quality. The scripted analysis then flattened all 702 use cases (471 safety, 231 nonsafety) into a single table, applied six quality checks, and clustered cleaned nonsafety rows using keyword matching on 227 rows that had evidence and non-generic labels.

---

## Data Quality: What to Trust

The extraction produced usable data, but there are meaningful reliability issues before drawing conclusions:

- **28 labels appeared in both the safety and nonsafety buckets.** For example, "assign and track safety actions with role-based access" and "track intervention impact with platform markers" were tagged as both safety and nonsafety in different calls. This level of cross-bucket bleed (12% of all unique nonsafety labels) suggests the extraction model had no consistent rule for the distinction.
- **9 label strings were exact duplicates across files** (e.g., "PPE compliance monitoring" appears in 8 separate calls). These likely reflect a small fixed vocabulary the LLM was anchored to rather than distinct customer expressions.
- **7 generic/admin labels** matched scheduling or follow-up language (e.g., "Getting sites onto the same schedule," "Timing follow-up around internal planning") — real workflow friction, but not product use cases.
- **4 files had only 1 extracted use case total**, suggesting either very short calls or incomplete extraction.
- **Zero-evidence use cases: 0.** Every extracted use case had at least one supporting quote — the one unambiguously clean signal in the dataset.

The cleaned nonsafety dataset (227 rows, 15% unclustered) is credible for directional conclusions, but not precise enough to stake hard product prioritization on without re-running extraction with a cleaner safety/nonsafety definition.

---

## Top 3 Non-Safety Opportunities

**1. Reporting & Analytics — 36 calls, 51 mentions**

Customers consistently want more from Voxel's data layer: executive dashboards, cross-site trend exports, platform adoption metrics, and email summaries for stakeholders who won't log in. The breadth here is the signal — 36 distinct calls raised it. One customer said: *"Being used and, you know, through the program, giving me all that data has been really helpful to really pinpoint with these managers."* Another flagged that a competitor's data was "very, very confusing," positioning Voxel's existing interface as a potential advantage if reporting is surfaced more deliberately. Voxel already captures the underlying data; the ask is mostly about access and presentation. This is low-lift to explore and has clear enterprise upsell implications.

**2. Operational Efficiency & Labor — 26 calls, 40 mentions**

Customers are using Voxel data to identify operational inefficiencies beyond safety — dock door duration, PIT parking time, dwell patterns, and freezer door monitoring for energy costs. One customer noted directly: *"I saved hundreds of thousands of dollars in energy just by noticing that there was a door that was two feet open in Modesto, California, about two days a week."* Another was actively measuring: *"The one area I wanted to highlight with you was parking duration, because that saw a pretty sharp increase this past month."* These are not hypothetical requests — customers are already pulling this data from Voxel's existing detections. The opportunity is to formalize it as a product surface rather than a workaround.

**3. Security & Loss Prevention — 16 calls, 18 mentions**

Shrink reduction and after-hours access monitoring came up across 16 calls — primarily retail and warehouse customers. Quotes are specific: *"That could have been shrink right there. So that product could have fell off and that could have been, you know, a loss for that."* And: *"I just simply would want to know when someone picks that up and walked away with it."* The evidence is thinner per call than in the top two clusters — most calls had one or two mentions rather than extended discussion — so confidence here is moderate. But the customer language was unprompted and tied to real loss numbers, which makes it worth watching.

---

## Recommended Pipeline Improvement

The biggest quality problem is the 28-label cross-bucket bleed between safety and nonsafety. A straightforward fix is to add a **definition check step** immediately after extraction: for any label that appears in both buckets across the dataset, flag it for human review before finalizing. In practice, this means building a small deduplication pass that compares extracted labels case-insensitively across all files in a batch run and surfaces conflicts in a review queue. This would take one engineer a day to implement and would give reviewers a targeted list rather than requiring full re-reads. It directly addresses the root issue — the LLM lacks a stable, consistent boundary between safety and non-safety applications — without requiring a full re-prompt.

---

## Assumptions

1. Each JSON file represents one unique customer call (no deduplication of calls across files was attempted).
2. Keyword-based clustering reflects customer intent accurately for the majority of labels — edge cases exist but do not materially change the top 3 ranking.
3. Breadth (number of distinct calls mentioning a cluster) is treated as a stronger signal than raw mention count, since a single call can inflate counts with multiple related labels.
