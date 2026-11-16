# Step 4: LLM extraction on Markdown

The tier asks for a structured product. Empty strings mean the field was missing. The default run uses `scripted_parse` so it stays offline. `python main.py --live` sends `sample_allbirds.md` through `OpenAiModel` and prints the token counts.

```
python main.py
python main.py --live
```
