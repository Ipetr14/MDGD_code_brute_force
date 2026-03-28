'''
Description: Python code for the brute force algorithm, version with the "bamboo" or "stick"
Author: Petr Myagkov
Modification Log:
    March 23, 2026: Created file wrote foundational function for html parsing (were mostly already implemented by Vishesh Prasad)
    March 24, 2026: Started implementing function for different rules that are required to draw edges
    March 26, 2026: Implemented the basic version of the algo, F1 around 41%, added a couple features like uniting together equations that don't have any words between them and dealing with contractions
'''

import os
import re
from bs4 import BeautifulSoup, NavigableString

import article_parser

def parse_html(html_path):
    """
    Parse HTML article and replace displayed numbered equations and inline
    references to numbered equations with `MATHMARKER`.

    Returns:
        text: plain text with equation markers
        equation_ids: list of numbered display equation IDs
        marker_equation_ids: equation IDs in the same order as the markers
        marker_is_display: booleans indicating whether each marker is a display
    """
    if not os.path.exists(html_path):
        return None, None, None, None

    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove citations from the text
    for cite in soup.find_all("cite"):
        cite.decompose()

    equation_ids = []
    marker_equation_ids = []
    marker_is_display = []
    seen_display_ids = set()

    # Replace equation references and display-math containers in document order.
    # Numbered displays and refs to numbered displays get a marker.
    # Unnumbered display expressions (e.g. S3.Ex7) are removed so their
    # internal MathML text does not inflate the word gap between equations.
    display_id_pattern = re.compile(r"^S\d+\.(E\d+|Ex\d+)$")
    numbered_equation_pattern = re.compile(r"^S\d+\.E\d+$")
    equation_ref_pattern = re.compile(r"^#(S\d+\.E\d+)$")

    for tag in soup.find_all(True):
        if tag.name == "a":
            href = tag.get("href", "")
            ref_match = equation_ref_pattern.fullmatch(href)
            if not ref_match:
                continue

            # References inside display equations are irrelevant because the
            # whole display container is handled separately.
            parent_display = tag.find_parent(
                ["table", "tbody"],
                id=display_id_pattern,
            )
            if parent_display is not None:
                continue

            marker_equation_ids.append(ref_match.group(1))
            marker_is_display.append(False)
            tag.replace_with(NavigableString(" MATHMARKER "))
            continue

        if tag.name not in {"table", "tbody"}:
            continue

        container_id = tag.get("id")
        if not container_id or not display_id_pattern.fullmatch(container_id):
            continue

        if container_id in seen_display_ids:
            continue

        seen_display_ids.add(container_id)

        if numbered_equation_pattern.fullmatch(container_id):
            equation_ids.append(container_id)
            marker_equation_ids.append(container_id)
            marker_is_display.append(True)
            tag.replace_with(NavigableString(" MATHMARKER "))
        else:
            tag.replace_with(NavigableString(" "))

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    # Remove References OR Acknowledgments (Last) section
    text = (text.rsplit("References", 1))[0]
    text = text.split("Acknowledgments")[0]

    return text, equation_ids, marker_equation_ids, marker_is_display

def tokenize_with_sentence_ids(text):
    """
    Tokenize text and assign each token a sentence number.

    Returns:
        tokens: list of tokens
        sentence_nums: sentence number for each token index
    """

    # pattern for one token, it can be our equation marker (MATHMAKER), sequence of letters, numbers and hyphens, 
    # end of sentence punctuation, or specific symbols
    pattern = r"MATHMARKER|[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*|[.!?]+|[^\w\s]"

    # pattern for the end of sentence
    pattern_sentence_end = r"[.!?]+"

    tokens = re.findall(pattern, text)

    # Common scientific abbreviations that often appear before numbers/labels
    # and should not trigger sentence boundaries (e.g., "Fig. 1", "Eq. (2)").
    base_non_terminal_abbrev = {
        "fig", "figs", "ref", "refs", "eq", "eqs",
        "sec", "secs", "ch", "chap", "app", "apps",
        "no", "nos", "def", "thm", "lem", "prop", "cor",
        "ex", "obs", "resp", "cf", "al",
    }
    non_terminal_abbrev = set()
    for abbrev in base_non_terminal_abbrev:
        non_terminal_abbrev.update({abbrev, abbrev.capitalize(), abbrev.upper()})

    def is_sentence_end_token(index):
        token = tokens[index]
        if not re.fullmatch(pattern_sentence_end, token):
            return False

        # Handle abbreviation + dot + label patterns in scientific text.
        if token == ".":
            prev_token = tokens[index - 1] if index > 0 else None

            if prev_token in non_terminal_abbrev:
                return False

        return True

    cnt = 0
    sentence_nums = []

    for idx, token in enumerate(tokens):
        sentence_nums.append(cnt)

        # increase id of current sentence if see the end of sentence
        if is_sentence_end_token(idx):
            cnt += 1
    
    return tokens, sentence_nums

def get_equation_positions(tokens, marker_equation_ids, marker_is_display):
    """
    Get the token position of each equation occurrence in the text.

    Return:
        equation_occurrences: array of tuples `(equation_id, token_id, is_display)`
    """
    token_pos = 0
    marker_pos = 0
    equation_occurrences = []

    for token in tokens:
        if token == "MATHMARKER":
            if marker_pos >= len(marker_equation_ids):
                raise ValueError("More MATHMARKER tokens found than recorded equation markers.")
            equation_occurrences.append(
                (marker_equation_ids[marker_pos], token_pos, marker_is_display[marker_pos])
            )
            marker_pos += 1

        token_pos += 1

    if marker_pos != len(marker_equation_ids):
        raise ValueError("Recorded equation markers do not match parsed MATHMARKER tokens.")

    return equation_occurrences

def is_word_token(token):
    """
    Checks whether the token is a word (for the threshold that equation must be close to each other to have connection)

    Return:
        is_word: boolean, true if token is a word, false if not
    """

    # if token is our equation marker, it is not a word
    if token == "MATHMARKER":
        return False

    #pattern for word (counts sequences that consists from letters, numbers and hyphens)
    word_pattern = r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*"

    is_word = re.fullmatch(word_pattern, token)

    return is_word

def count_gap_words(tokens, left_pos, right_pos):
    """
    Counts amount of words in the subsegment [left_pos, right_pos] in the array of tokens

    Return:
        words_cnt: int, representing the amount of words in the subsegment
    """

    words_cnt = 0

    for pos in range(left_pos, right_pos + 1):

        # if current token is a word we increase the answer
        if is_word_token(tokens[pos]):
            words_cnt += 1

    return words_cnt

def has_2_full_sentence_between(left_pos, right_pos, sentence_nums):
    """
    Check whether there are 2 full sentences between 2 tokens, located at left_pos and right_pos

    Return:
        full_sentence_between: boolean, True if 2 full sentences are present, False if not
    """

    # presence of at least 1 full sentence between 2 tokesn is equivalent to condition than the numbers of sentences
    # where the tokens are located, differs at least by 2
    full_sentence_between = (sentence_nums[right_pos] - sentence_nums[left_pos] >= 3)

    return full_sentence_between

def build_local_adjacency(equations, tokens, sentence_nums, max_gap):
    """
    Build an adjacency list using the set of rules:

    Adding edge between 2 equations:
    - equations are consecutive in document order, unless several consecutive equations
      have no real words between them and are treated as one local system
    - no full sentence in between
    - number of words in between is <= max_gap

    Return:
        adjacency: dictionary from int to list of ints, representing the desired adjacency list
    """
    adjacency = {}

    if not equations:
        return adjacency

    current_system = [equations[0][0]]

    for ind in range(len(equations) - 1):
        left_id, left_idx, left_is_display = equations[ind]
        right_id, right_idx, right_is_display = equations[ind + 1]

        gap_words = count_gap_words(tokens, left_idx, right_idx)
        full_sentence_between = has_2_full_sentence_between(left_idx, right_idx, sentence_nums)

        # Consecutive equations with no real words between them are grouped into one system.
        if gap_words <= 2:
            current_system.append(right_id)
        else:
            if gap_words <= max_gap and not full_sentence_between and right_is_display:
                for equation_id in current_system:
                    if equation_id != right_id:
                        adjacency.setdefault(equation_id, []).append(right_id)
            current_system = [right_id]

    return adjacency

def get_full_adj_list(old_adj_list, equation_ids):
    """
    Normalize an adjacency list keyed by equation IDs and ensure every displayed
    numbered equation appears in the output.

    Return:
        full_adj_list: dictionary from str to list of strs, representing new desired adjacency list
    """
    full_adj_list = {}
    for src_id in equation_ids:
        dst_ids = []
        seen_dst_ids = set()

        for dst_id in old_adj_list.get(src_id, []):
            if dst_id not in seen_dst_ids:
                seen_dst_ids.add(dst_id)
                dst_ids.append(dst_id)

        if dst_ids:
            full_adj_list[src_id] = dst_ids
        else:
            full_adj_list[src_id] = [None]

    return full_adj_list

def brute_force_algo():
    """
    Run the "bamboo/stick" brute force algorithm on all manually parsed articles.

    Returns:
        article_ids: list of strs, representing all articles that were used for testing
        true_adjacency_lists: list of dictionaries, representing adjacency lists from the dataset
        predicted_adjacency_lists: list of dictionaries, representing adjacency lists created by the brute force
    """
    articles_dir = "articles"
    max_gap = 400
    articles = article_parser.get_manually_parsed_articles()

    article_ids = []
    true_adjacency_lists = []
    predicted_adjacency_lists = []

    for article_id, article in articles.items():
        html_path = os.path.join(articles_dir, f"{article_id}.html")

        text, equation_ids, marker_equation_ids, marker_is_display = parse_html(html_path)
        if (
            text is None
            or equation_ids is None
            or marker_equation_ids is None
            or marker_is_display is None
        ):
            continue

        tokens, sentence_nums = tokenize_with_sentence_ids(text)
        equations = get_equation_positions(tokens, marker_equation_ids, marker_is_display)

        if len(equations) != len(marker_equation_ids):
            print(
                f"Skipping {article_id}: "
                f"{len(equations)} markers found but {len(marker_equation_ids)} equation markers collected."
            )
            continue

        local_adj = build_local_adjacency(
            equations=equations,
            tokens=tokens,
            sentence_nums=sentence_nums,
            max_gap=max_gap,
        )

        predicted_adj = get_full_adj_list(local_adj, equation_ids)

        article_ids.append(article_id)
        true_adjacency_lists.append(article["Adjacency List"])
        predicted_adjacency_lists.append(predicted_adj)

    return article_ids, true_adjacency_lists, predicted_adjacency_lists
