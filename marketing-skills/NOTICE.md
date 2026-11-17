# Marketing skills (vendored)

`skills/` holds a selection of the "marketingskills" pack by Corey Haines (MIT, see `LICENSE`), copied unmodified:
product-marketing, content-strategy, social, copywriting, copy-editing, marketing-psychology, offers, lead-magnets, customer-research, marketing-ideas.
`src/marketingskills.py` loads them and hardcodes their rules into the pipeline; `config/marketing.json` is the shared marketing brief (the product-marketing context) that every output reads.
The loader strips tool-registry and sponsor sections, so the agent never promotes third-party tools.
