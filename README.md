# MDGD Brute-Force Derivation Graph

This repository contains the current rule-based derivation-graph baseline for the MDGD project. It reads locally stored article HTML, extracts equation occurrences from the paper text, predicts directed edges between displayed equations, evaluates those predictions against `articles.json`, and writes the results to JSON.

## What The Current Algorithm Does

The implemented pipeline is the brute-force baseline in [`brute_force.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py). For each article it:

1. Parses the HTML with BeautifulSoup.
2. Removes citation tags.
3. Replaces numbered displayed equations such as `S0.E3` with a `MATHMARKER`.
4. Replaces inline references like links to `#S0.E3` with a `MATHMARKER` as well.
5. Removes unnumbered display blocks so their MathML text does not artificially increase the gap between equations.
6. Collapses the paper into plain text, then trims content after `References` or `Acknowledgments`.
7. Tokenizes the text and assigns each token a sentence index, with special handling so abbreviations like `Fig.` or `Eq.` do not incorrectly end a sentence.
8. Walks through equation-marker occurrences in document order and builds edges with local heuristics.

## Edge Construction Rules

The graph-building logic lives in `build_local_adjacency(...)` in [`brute_force.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py).

- Consecutive equation occurrences are processed in document order.
- If two consecutive occurrences have at most 2 word tokens between them, they are grouped into the same local "system".
- When the gap is larger than 2 words, the algorithm may connect the current system to the next occurrence only if:
  - the gap is at most `max_gap = 400` words,
  - there are not two full sentence boundaries between them,
  - and the target occurrence is a displayed numbered equation.
- If a connection is allowed, every equation currently in the local system gets an edge to that displayed equation.
- Final output is normalized so every displayed numbered equation from the paper appears in the adjacency list. Equations with no outgoing edge are stored as `[null]` in JSON.

Inline equation references affect locality because they are kept as marker occurrences during parsing, but the final adjacency list is keyed only by displayed numbered equations.

## Repository Layout

- [`brute_force.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/brute_force.py): HTML parsing, tokenization, locality rules, and brute-force graph construction.
- [`derivation_graph.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py): command-line entry point and evaluation logic.
- [`article_parser.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/article_parser.py): loads the manually labeled article set from `articles.json`.
- [`results_output.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/results_output.py): writes evaluation output JSON.
- [`articles.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles.json): manually parsed articles and ground-truth adjacency lists.
- [`articles/`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles): local HTML files used as input.
- [`outputs/Brute_Force/brute_force.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/outputs/Brute_Force/brute_force.json): saved output from the brute-force run.

## Requirements

Install the Python packages used by the current code:

```bash
pip install beautifulsoup4 numpy pytz
```

Run with `python3`.

## How To Run

```bash
python3 derivation_graph.py -a brute
```

This run:

- loads the labeled articles from `articles.json`,
- parses matching HTML files from `articles/`,
- predicts adjacency lists with the brute-force baseline,
- evaluates the predictions against ground truth,
- writes results to `outputs/Brute_Force/brute_force.json`.

## Output Structure

The generated JSON has two top-level sections:

- `Correctness`: overall and aggregate evaluation statistics.
- `Results`: one entry per article with the predicted adjacency list and per-article metrics.

Each adjacency list maps a displayed equation ID to a list of derived equation IDs. If no outgoing edges are predicted, the stored value is `[null]`.

## Notes

- The repository is currently centered on the brute-force baseline. Although [`derivation_graph.py`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/derivation_graph.py) still exposes older algorithm flags, the execution path in this repo calls `brute_force.brute_force_algo()`.
- The article metadata in [`articles.json`](/Users/petrmyagkov/Documents/UIUC/MDGD/code_mdgd/articles.json) currently lists 107 manually parsed articles.
