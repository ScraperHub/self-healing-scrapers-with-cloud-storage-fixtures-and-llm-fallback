# Step 6: drift detection

The store keeps one row per field, tier, and crawl. The detector compares the last day with the seven days before it. An incident needs the CSS fill rate to fall by more than 30 points while the LLM fill rate stays within 10 points. Rows whose status is not 200 are ignored.

```
python main.py
```
