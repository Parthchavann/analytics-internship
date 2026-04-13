# Submission Notes — Parth Chavan

I started by reading eight JSON files manually before writing any code — I wanted to see what a typical label looked like and identify structural problems before the script could obscure them. The first thing I noticed was that the safety/nonsafety boundary was inconsistent: labels like "assign and track safety actions" appeared in both buckets, which affects every downstream cluster count.

The script runs seven quality checks and introduces two things I haven't seen in standard take-homes: a Jaccard similarity pass to catch near-duplicate labels (e.g., three different labels all describing "door open duration monitoring"), and speaker attribution — tagging whether each evidence quote came from a customer or a Voxel rep. That last one matters because 32% of nonsafety use cases had zero customer quotes. Those are use cases a Voxel rep described, not ones a customer requested. Treating them equally inflates confidence in the findings.

I chose keyword clustering over embeddings for inspectability — the rules are readable and arguable, which matters when presenting findings to stakeholders. The tradeoff is that synonymous labels with no keyword overlap get missed. With more time I'd layer in semantic clustering to catch those, cross-reference findings with deal stage or tenure metadata, and build a per-use-case confidence score that weights customer-initiated evidence more heavily than Voxel-prompted evidence.

Tools: Python, pandas, regex, json.tool for manual inspection.
