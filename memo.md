# Non-Safety Opportunities in Voxel Customer Calls
**Parth Chavan | April 2026**

---

## Dataset & Approach

92 customer calls (99 JSON files, 7 with no extracted use cases) were analyzed, yielding 702 total use cases — 471 safety, 231 nonsafety. Before writing any code, I read 8 files manually to map the schema, understand label style, and spot cross-bucket inconsistencies. The script then applied 7 quality checks, attributed each evidence quote to either a Voxel rep or a customer speaker, and clustered 229 cleaned nonsafety rows using keyword-based theme assignment. Clusters were validated against a top-30 label frequency check and a Jaccard near-duplicate audit before drawing conclusions.

---

## Data Quality: What to Trust

The extraction is directionally useful but has four reliability problems that affect how much weight any single label should carry:

- **24 calls (26%) have the same label in both safety and nonsafety buckets.** Labels like "enterprise safety analytics and summary view" and "assign and track safety actions with role-based access" appear in both buckets across different calls — the extractor had no stable boundary between the two categories.
- **26 nonsafety labels contain explicit safety-core language** (e.g., "Retail floor hazard detection to reduce liability exposure," "Reduce injury and liability costs via targeted interventions") — these are safety use cases mislabeled as nonsafety.
- **17 near-duplicate label pairs detected via Jaccard similarity ≥ 0.45** (e.g., "Open door duration monitoring" ≈ "Dock door open-duration tracking" ≈ "Door open/propped duration monitoring"). Label fragmentation inflates apparent variety — these are the same use case described three different ways.
- **34 use cases have at least one evidence quote under 35 characters** — too short to confirm the label actually reflects the customer's intent.
- **32% of nonsafety use cases (74 of 231) have zero customer quotes** — all evidence comes from Voxel reps describing the use case, not customers requesting it. These are weaker signals and were tracked separately throughout the analysis.

The cleaned nonsafety dataset (229 rows, 14% unclustered) is reliable enough for directional product prioritization, but individual label counts should be treated as lower bounds, not precise measurements.

---

## Top 3 Non-Safety Opportunities

**1. Reporting & Analytics — 40 calls (43.5%), 61 mentions**

Customers want more from Voxel's data layer: executive dashboards, PDF/CSV exports, cross-site benchmarking, email summaries for stakeholders who won't log in, and platform adoption metrics. This showed up in nearly half of all calls analyzed, and the requests were specific. One customer: *"Being used and, you know, through the program, giving me all that data has been really helpful to really pinpoint with these managers."* Another flagged a competitor's interface as "very, very confusing," positioning Voxel's existing data as an advantage if surfaced better. 20 of 61 mentions had Voxel-rep-only evidence, so roughly two-thirds of these requests were customer-initiated — a strong signal. Voxel already captures the underlying data; this is an access and presentation problem, not a detection problem.

**2. Operational Efficiency & Labor — 25 calls (27.2%), 36 mentions**

Customers are repurposing Voxel's existing camera coverage for operational visibility: dock door duration, PIT vehicle dwell time, freezer door monitoring for energy costs, and conveyor congestion detection. One customer was explicit about the financial case: *"I saved hundreds of thousands of dollars in energy just by noticing that there was a door that was two feet open in Modesto, California, about two days a week."* Another: *"once we have a jam, I would wonder if there's an ability to go back in time and say, look, this is the five seconds before that jam happened."* 13 of 36 mentions had Voxel-rep-only evidence, so about a third were prompted. Still, the dollar amounts cited and operational specificity of the requests make this a credible expansion surface.

**3. Workflow & Action Management — 18 calls (19.6%), 21 mentions**

Customers want a structured execution layer inside Voxel: assign clips to owners, set due dates, send automated reminders, and track resolution. The evidence is clear and customer-voiced: *"Since we assign a due date, what happens when that due date passes? Is there reminders?"* A Voxel rep confirmed the gap: *"The one thing we don't have that we've heard from a lot of folks is reminders for past due — how do we nudge someone when something's past due?"* This theme is distinct from the others because it's about workflow closure, not detection or data access. Confidence is moderate — 18 calls is a real signal, but some action management labels bled into Reporting & Analytics via the "boards" keyword, so the true count may be slightly higher.

**Notable signal worth watching:** Security & Loss Prevention appeared in only 3 calls in 2022 and 3 in 2023, but jumped to 10 distinct calls in 2024. Too early to rank it in the top 3, but the acceleration is worth flagging.

---

## Recommended Pipeline Improvement

**Add a speaker-attribution filter before finalizing use case extractions.** 32% of nonsafety use cases in this dataset have zero customer quotes — the evidence is entirely Voxel reps describing a capability, not customers requesting one. A simple post-processing step that tags each extracted use case as "customer-initiated" or "Voxel-prompted" (based on speaker email domain) would let reviewers immediately separate genuine demand signals from sales-side framing. This requires no changes to the extraction model — just a labeling pass on the output JSON before it enters any analysis. It would meaningfully raise the confidence bar on downstream prioritization decisions.

---

## Assumptions

1. Each JSON file is a unique customer call — no cross-file deduplication was attempted.
2. Speaker email domain (`voxelai.com` vs. customer domain) is a reliable proxy for whether a use case was customer-initiated or Voxel-prompted.
3. Call breadth (distinct files per theme) is treated as a stronger signal than raw mention count; one call can surface many related labels, which would overstate frequency without this normalization.
