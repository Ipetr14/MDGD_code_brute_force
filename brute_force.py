'''
Description: Python code for the brute force algorithm, version with the "bamboo" or "stick"
Author: Petr Myagkov
Modification Log:
    March 23, 2026: Created file wrote foundational function for html parsing (were mostly already implemented by Vishesh Prasad)
    March 24, 2026: Started implementing function for different rules that are required to draw edges
'''

import os
import re
from bs4 import BeautifulSoup, NavigableString

import article_parser

def parse_html_for_proximity(html_path):
    """
    Parse HTML article, that is located at html_path, and replace each equation with 'MATHMARKER'.

    Returns:
        text: plain text with equation markers
        equation_ids: list of equation IDs in the same order as the markers
    """
    if not os.path.exists(html_path):
        return None, None

    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove citations from the text
    for cite in soup.find_all("cite"):
        cite.decompose()

    equation_ids = []
    seen_ids = set()

    # Same general approach as before:
    # find td[rowspan], then climb to a table/tbody container with an id.
    equation_cells = soup.find_all("td", attrs={"rowspan": True})

    for cell in equation_cells:
        container = cell.find_parent(["table", "tbody"])

        while container is not None and not container.get("id"):
            container = container.find_parent(["table", "tbody"])

        if container is None:
            continue

        equation_id = container.get("id")
        if not equation_id or equation_id in seen_ids:
            continue

        seen_ids.add(equation_id)
        equation_ids.append(equation_id)

        # Replace the whole equation block with one marker.
        container.replace_with(NavigableString(" MATHMARKER "))

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    # Remove References OR Acknowledgments (Last) section
    text = (text.rsplit("References", 1))[0]
    text = text.split("Acknowledgments")[0]

    return text, equation_ids

def tokenize_with_sentence_ids(text):
    """
    Tokenize text and assign each token a sentence id.

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
    cnt = 0
    sentence_nums = []

    for token in tokens:
        sentence_nums.append(cnt)

        # increase id of current sentence if see the end of sentence
        if re.fullmatch(pattern_sentence_end, token):
            cnt += 1
    
    return tokens, sentence_nums

def get_equation_positions(tokens):
    """
    Get position of each equation in the array of tokens, as well as its position among all equations in the text

    Return:
        equations_nums: array of tuples (eq_num, token_id), represents the number of equation among all equations, 
        and among all tokens
    """
    # position of token we currently looking at
    token_pos = 0

    # position of equation we currently looking at
    equation_pos = 1

    equation_nums = []

    for token in tokens:

        # if we see equation marker, we add to our array its position among equations and tokens
        if token == "MATHMARKER":
            equation_nums.append((equation_pos, token_pos))
            equation_pos += 1

        # moving to the next token in the array "tokens"
        token_pos += 1

    return equation_nums

def is_word_token(token):
    """
    Checks whether the token is a word (for the threshold that equation must be close to each other to have connection)

    Return:
        is_word: boolean, true if token is a word, false if not
    """

    # if token is our equation marker, it is not a word
    if token == "MATHMAKER":
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

def has_full_sentence_between(left_pos, right_pos, sentence_nums):
    """
    Check whether there is a full sentence between 2 tokens, located at left_pos and right_pos

    Return:
        full_sentence_between: boolean, True if full sentence present, False if not
    """

    # presence of at least 1 full sentence between 2 tokesn is equivalent to condition than the numbers of sentences
    # where the tokens are located, differs at least by 2
    full_sentence_between = (sentence_nums[right_pos] - sentence_nums[left_pos] >= 2)

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
        left_num, left_idx = equations[ind]
        right_num, right_idx = equations[ind + 1]

        gap_words = count_gap_words(tokens, left_idx, right_idx)
        full_sentence_between = has_full_sentence_between(left_idx, right_idx, sentence_nums)

        # Consecutive equations with no real words between them are grouped into one system.
        if gap_words == 0:
            current_system.append(right_num)
        else:
            if gap_words <= max_gap and not full_sentence_between:
                for equation_num in current_system:
                    adjacency.setdefault(equation_num, []).append(right_num)
            current_system = [right_num]

    return adjacency

def get_full_adj_list(old_adj_list, equation_nums):
    """
    Convert an internal adjacency list using equation numbers into an adjacency list using real equation IDs

    Return:
        full_adj_list: dictionary from str to list of strs, representing new desired adjacency list
    """
    full_adj_list = {}
    num_equations = len(equation_nums)

    for src_num, src_id in enumerate(equation_nums, start=1):
        dst_ids = []

        for dst_num in old_adj_list.get(src_num, []):
            if 1 <= dst_num and dst_num <= num_equations:
                dst_ids.append(equation_nums[dst_num - 1])

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
    max_gap = 40
    articles = article_parser.get_manually_parsed_articles()

    article_ids = []
    true_adjacency_lists = []
    predicted_adjacency_lists = []

    for article_id, article in articles.items():
        html_path = os.path.join(articles_dir, f"{article_id}.html")

        text, equation_ids = parse_html_for_proximity(html_path)
        if text is None or equation_ids is None:
            continue

        tokens, sentence_nums = tokenize_with_sentence_ids(text)
        equations = get_equation_positions(tokens)

        if len(equations) != len(equation_ids):
            print(
                f"Skipping {article_id}: "
                f"{len(equations)} markers found but {len(equation_ids)} equation IDs collected."
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
