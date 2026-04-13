# Submission Notes — Parth Chavan

I started by reading eight JSON files manually before writing any code — I wanted to see what a typical label looked like and catch obvious problems first. What stood out immediately was that the safety/nonsafety boundary was blurry: labels like "assign and track safety actions" appeared in both buckets, which affects how much you can trust any downstream clustering.

The script runs six quality checks, flattens everything into findings.csv, and clusters nonsafety use cases using keyword matching. I chose keywords over embeddings because the rules are readable and arguable — with embeddings you get tighter groups but lose the ability to explain a placement quickly, which matters when presenting findings.

The top three clusters held across multiple refinement passes. Reporting & Analytics and Operational Efficiency led on call breadth (36 and 26 calls). Security & Loss Prevention is real but thinner — specific quotes, but most calls raised it only once.

With more time I'd run semantic clustering to catch synonymous labels, cross-reference findings with deal stage or tenure metadata, and add a confidence score per use case based on evidence length and whether the quote came from the customer or the Voxel rep.

Tools: Python, pandas, regex, json.tool.
