# MDGD Brute-Force Derivation Graph

This repository contains the current rule-based derivation-graph baseline for the MDGD project. It reads locally stored article HTML, extracts equation occurrences from paper text, predicts directed edges between displayed equations, evaluates those predictions against `articles.json`, and writes the results to JSON.

## Current Brute-Force Pipeline

The active `brute` execution path is split across [`brute_force.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py) and [`derivation_graph.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py).

When you run:

```bash
python3 derivation_graph.py -a brute
```

the code currently does this:

1. Loads the manually labeled article set from `articles.json`.
2. Parses each matching HTML file from `articles/` with BeautifulSoup.
3. Removes citation tags.
4. Replaces numbered displayed equations such as `S0.E3` with `MATHMARKER`.
5. Replaces inline references to numbered equations such as `#S0.E3` with `MATHMARKER`.
6. Removes unnumbered display blocks so their MathML content does not inflate equation gaps.
7. Collapses the article into plain text and trims trailing `References` or `Acknowledgments`.
8. Tokenizes the text and assigns a sentence index to each token, with abbreviation handling for patterns such as `Fig.` and `Eq.`.
9. Builds a cached representation of equation-to-equation transitions for all usable articles.
10. Tunes the brute-force thresholds over the cached data in [`tune_brute_force_vars()`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py:303).
11. Re-evaluates the best predicted adjacency lists and writes the final report to [`outputs/Brute_Force/brute_force.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/outputs/Brute_Force/brute_force.json).

## Edge Construction Rules

The local graph-building rules live in [`build_local_adjacency(...)`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py:267).

- Equation occurrences are processed in document order.
- If two consecutive occurrences have at most 2 word tokens between them, they are grouped into the same local equation system.
- When the gap is larger than 2 words, the algorithm may connect the current system to the next occurrence only if the target is a displayed numbered equation and both gap thresholds are satisfied.
- If a connection is allowed, every equation currently in the local system gets an edge to that displayed equation.
- The final adjacency list is normalized so every displayed numbered equation in the article appears as a key.
- Equations with no predicted outgoing edges are stored as `[null]` in the output JSON.

Inline references affect locality because they remain as equation-marker occurrences during parsing, but only displayed numbered equations appear as top-level keys in the final adjacency list.

## Threshold Tuning

The current brute-force run does not use one fixed hand-written threshold pair.

[`tune_brute_force_vars()`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py:303) first caches article transitions, then searches over candidate thresholds derived from the observed data:

- word-gap candidates are collected up to `BRUTE_FORCE_MAX_WORD_GAP_LIMIT = 500`
- sentence-gap candidates are collected up to `BRUTE_FORCE_MAX_SENTENCE_GAP_LIMIT = 10`

For each candidate pair, the code evaluates the predicted adjacency lists with [`evaluate_adjacency_lists()`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py:104) and selects the pair with the best overall F1 score. The chosen pair is printed to the console before the final JSON is written.

## Current Reported Metrics

The current saved brute-force report in [`outputs/Brute_Force/brute_force.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/outputs/Brute_Force/brute_force.json) reports:

- `Overall Correctness -> Overall F1 Score = 0.5424354243542435`
- `Aggregate Correctness Statistics -> F1 Score -> Mean = 0.5397241674132537`
- `Number of articles used = 69`

These two F1 values are intentionally different:

- `Overall F1 Score` is computed once from global totals across all articles.
- `F1 Score -> Mean` is the arithmetic mean of the per-article F1 scores.

If you describe the current brute-force baseline as "about 0.54 F1", that matches the present output better than the older README wording about a fixed `53%`.

## Repository Layout

- [`brute_force.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py): HTML parsing, tokenization, locality rules, and brute-force graph construction.
- [`derivation_graph.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py): command-line entry point, threshold tuning, and evaluation logic.
- [`article_parser.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/article_parser.py): loads the manually labeled article set from `articles.json`.
- [`results_output.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/results_output.py): writes evaluation output JSON.
- [`articles.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles.json): manually parsed articles and ground-truth adjacency lists.
- [`articles/`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles): local HTML files used as input.
- [`outputs/Brute_Force/brute_force.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/outputs/Brute_Force/brute_force.json): saved output from the latest brute-force run in the working tree.

## Requirements

Install the Python packages used by the current code:

```bash
pip install beautifulsoup4 numpy pytz
```

Run with `python3`.

## Output Structure

The generated JSON has two top-level sections:

- `Correctness`: dataset-level metrics and aggregate per-article statistics.
- `Results`: one entry per article with the predicted adjacency list and per-article metrics.

Inside `Correctness`, note the distinction between:

- `Overall Correctness`: metrics computed from global totals over the full dataset.
- `Aggregate Correctness Statistics`: summary statistics over the per-article metric lists.

## Notes

- The repository is currently centered on the brute-force baseline. Although [`derivation_graph.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py) still exposes older algorithm flags, the `brute` path now runs threshold tuning before saving the final report.
- The article metadata in [`articles.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles.json) currently lists 107 manually parsed articles, while the current brute-force output uses 69 articles.
