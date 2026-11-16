# Step 2: Crawlbase scraper tier and store=true

`sample_amazon.json` is a trimmed `amazon-product-details` payload. The default run maps it offline. `python main.py --live` also crawls `https://example.com` with `store=true` and prints the `rid` taken from the `storage_url` query string. The token stays in `.env`.

```
python main.py
python main.py --live
```
