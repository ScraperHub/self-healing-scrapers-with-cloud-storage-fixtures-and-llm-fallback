# Step 5: the tier chain

`TierChain.run` keeps the first tier whose product clears a fill rate of 0.75. A complete page stops at CSS, so the LLM tier is never called. A page the selectors cannot read falls through.

```
python main.py
```
