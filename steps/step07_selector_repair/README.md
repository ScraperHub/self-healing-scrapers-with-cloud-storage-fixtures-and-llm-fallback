# Step 7: propose selectors, validate them, write a diff

The offline run checks a known-good pair of selectors against two snapshots of the same template. The diff is written under `repair_out/` and is not applied. `python main.py --live` asks the model for selectors and accepts them only when title and price fill on both snapshots.

```
python main.py
python main.py --live
```
