# Step 8: replay stored pages

`manifest.json` points at two mirrored HTML files. `pytest` and `python main.py` both extract title and price from those files with no network. `python main.py --live` stores `https://example.com` and reads that same `rid` back from the Storage API.

```
python main.py
python main.py --live
pytest
```
