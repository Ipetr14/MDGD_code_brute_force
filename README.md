# MDGD Brute-Force Derivation Graph

This repository contains my brute-force implementation for the MDGD project. The goal is to infer a derivation graph between equations in STEM papers by parsing article HTML files, identifying equations in document order, and predicting which equations directly derive from earlier ones.

## Repository Purpose

The code in this repo focuses on one specific baseline: a local, rule-based "bamboo/stick" brute-force algorithm. It works from article structure and nearby text.

Given an article, algorithm follows this list:

1. Parses the HTML paper.
2. Replaces displayed equations with a `MATHMARKER` token.
3. Tracks the original equation IDs in article order.
4. Tokenizes the surrounding text and sentence boundaries.
5. Connects nearby consecutive equations when:
   - they are close in the text,
   - there is no full sentence between them,
   - and the gap contains at most a fixed number of words.
6. Evaluates the predicted adjacency list against manually labeled ground truth from `articles.json`.

## Main Files

- `brute_force.py`: core brute-force derivation graph algorithm.
- `derivation_graph.py`: command-line entry point that runs the algorithm and evaluates predictions.
- `article_parser.py`: utilities for loading the manually parsed dataset and extracting equations from article HTML.
- `results_output.py`: writes evaluation results to JSON.
- `articles.json`: labeled article metadata and ground-truth adjacency lists.
- `articles/`: local HTML copies of the papers used in evaluation.
- `outputs/Brute_Force/brute_force.json`: current saved output of the brute-force run.

## Algorithm Summary

The brute-force method in `brute_force.py` uses a simple locality heuristic:

- Equations are read in document order.
- Consecutive equations with no real words between them are treated as part of the same local system.
- An edge is added only when the next equation is still locally connected to the current system.
- The current implementation uses `max_gap = 40`, meaning two candidate equations can be linked only if there are at most 40 word tokens between them.

This makes the method easy to interpret and fast to run, while still serving as a useful baseline for derivation graph prediction.

## Requirements

Install the Python dependencies used directly by the code:

```bash
pip install beautifulsoup4 numpy pytz
```

The project is currently run with `python3`.

## How To Run

Run the brute-force derivation graph pipeline with:

```bash
python3 derivation_graph.py -a brute
```

This will:

- load the manually parsed articles from `articles.json`,
- process the corresponding HTML files in `articles/`,
- compute predicted adjacency lists using the brute-force algorithm,
- evaluate the predictions against the labeled derivation graphs,
- and write the results to `outputs/Brute_Force/brute_force.json`.

## Output Format

The generated JSON output contains two main sections:

- `Correctness`: overall metrics and aggregate per-article statistics.
- `Results`: predicted adjacency list and per-article metrics for each article.

Adjacency lists are stored as a dictionary from equation ID to a list of derived neighbor equation IDs. If an equation has no outgoing edge, it is recorded as `[null]` in JSON.

## Notes

- The repository currently includes generated files such as `__pycache__/` and `.DS_Store` because they were present in the working folder when the repository was created.
- This repo is oriented around local experimentation and evaluation on the included article set.
