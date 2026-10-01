# Expense Categorization Evaluation

## Approach

The categorizer is deterministic and rule-based; it has no trained model or training split. It applies Unicode normalization and case folding, removes common currency and amount tokens, normalizes punctuation and whitespace, then matches bounded phrases from a structured category/subcategory rule table. More-specific phrases take precedence over phrases contained within them. If there is no evidence, or similarly strong evidence points to different categories, the result is `Other`.

The returned confidence is a hand-set evidence-strength score from 0 to 1. It is not a calibrated probability. Unknown descriptions receive 0.15; ambiguous cross-category evidence receives 0.25.

## Held-Out Evaluation

Run with:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_expense_categorizer.py
```

The fixed JSON evaluation set contains 90 synthetic descriptions, balanced across the nine categories (10 per category). It is separate from the unit-test parameter cases. Since no model is trained, there is no train/test split; the file is a held-out regression set used only for evaluation. The examples were curated for supported phrases and are not a random or externally labeled transaction sample.

Results from the committed evaluator:

| Metric | Result |
| --- | ---: |
| Accuracy | 1.0000 |
| Macro precision | 1.0000 |
| Macro recall | 1.0000 |
| Macro F1 | 1.0000 |
| Weighted precision | 1.0000 |
| Weighted recall | 1.0000 |
| Weighted F1 | 1.0000 |
| Predicted `Other` | 10 / 90 (11.11%) |

All 10 examples in the `Other` class remained `Other`; all other categories had 10/10 correct on this set.

## Limitations

The perfect score reflects a small, curated phrase-coverage benchmark, not expected real-world accuracy. Merchant aliases, regional transaction formats, mixed-language text, and new payment descriptors can still be missed. Confidence scores are heuristic evidence strengths and should not be interpreted as calibrated probabilities. Expand and independently label the evaluation set before using these results for operational decisions.