# Submission Notes — Parth Chavan

I started by reading eight JSON files manually before touching Python. That was deliberate — I wanted to understand the schema, see what a "typical" use case label actually looked like, and spot obvious problems before writing code that might obscure them. What I noticed first was that the safety/nonsafety boundary was blurry: labels like "assign and track safety actions" showed up in both buckets. I flagged that early because it affects how much you can trust the clustering downstream.

The script (analysis.py) does six quality checks, flattens everything into findings.csv, and assigns nonsafety use cases to clusters using keyword matching. I chose keyword clustering over embeddings for two reasons: it's inspectable (you can read the rules and argue with them), and I had a few hours, not a few days. With embedding-based clustering you get tighter groups, but you lose the ability to quickly explain why something landed where it did — which matters if you're trying to convince someone to act on a finding.

The top three clusters held up across multiple passes of refinement. Reporting & Analytics and Operational Efficiency came out clearly ahead on call breadth (36 and 26 calls respectively). Security & Loss Prevention is real but thinner — the quotes are specific, but most calls only raised it once.

With more time I'd do three things: run semantic clustering to catch labels that mean the same thing but don't share keywords; cross-reference the nonsafety findings with deal stage or customer tenure if that metadata exists; and build a confidence score per use case based on evidence length and speaker attribution, since some quotes are clearly Voxel-side prompting rather than genuine customer requests.

Tools used: Python, pandas, regex, and json.tool for manual inspection.
