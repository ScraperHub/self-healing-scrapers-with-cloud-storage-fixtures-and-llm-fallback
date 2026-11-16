# Step 1: schema and extractor protocol

`ProductSchema` is the contract every tier has to fill. `fill_rate` is filled fields divided by the eight tracked fields. Blank strings count as empty. An extractor is a small protocol with one method, so later tiers can be tested without HTTP.

```
python main.py
```
