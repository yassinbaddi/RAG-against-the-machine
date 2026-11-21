import ast
import json
import textwrap
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

DATASET_FILE = Path(
    "/home/ybaddi/RAG/data/datasets_public/public/"
    "AnsweredQuestions/dataset_code_public.json"
)

PROJECT_ROOT = Path("/home/ybaddi/RAG")


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"


# ============================================================
# AST HELPERS
# ============================================================

def normalize_code(code: str) -> str:
    """
    Normalize code so that indentation and whitespace differences
    don't prevent a match.
    """
    code = textwrap.dedent(code)

    lines = []
    for line in code.splitlines():
        line = line.strip()

        # Ignore completely empty lines
        
        if line:
            lines.append(line)

    return "\n".join(lines)


def ast_fingerprint(code: str):
    """
    Convert code into an AST fingerprint.

    Returns None if the snippet cannot be parsed.
    """
    try:
        tree = ast.parse(textwrap.dedent(code))

        return ast.dump(
            tree,
            annotate_fields=True,
            include_attributes=False,
        )

    except SyntaxError:
        return None


def get_node_source(source: str, node: ast.AST) -> str:
    """
    Extract the exact source corresponding to an AST node.
    """

    if not hasattr(node, "lineno"):
        return ""

    if not hasattr(node, "end_lineno"):
        return ""

    lines = source.splitlines(keepends=True)

    start_line = node.lineno - 1
    end_line = node.end_lineno - 1

    selected = lines[start_line:end_line + 1]

    if not selected:
        return ""

    # Remove characters before col_offset on first line
    selected[0] = selected[0][node.col_offset:]

    # Remove characters after end_col_offset on last line
    selected[-1] = selected[-1][:node.end_col_offset]

    return "".join(selected)


def position_to_character_index(source: str, lineno: int, col: int) -> int:
    """
    Convert AST's (line, column) position to an absolute
    character index in the original source file.
    """

    lines = source.splitlines(keepends=True)

    return sum(len(line) for line in lines[:lineno - 1]) + col


def get_node_indexes(source: str, node: ast.AST):
    """
    Return absolute character indexes for an AST node.
    """

    start = position_to_character_index(
        source,
        node.lineno,
        node.col_offset,
    )

    end = position_to_character_index(
        source,
        node.end_lineno,
        node.end_col_offset,
    )

    return start, end


# ============================================================
# AST NODE COLLECTION
# ============================================================

def collect_ast_nodes(tree: ast.AST):
    """
    Collect AST nodes that can represent useful RAG chunks.
    """

    nodes = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.Return,
                ast.Raise,
                ast.Import,
                ast.ImportFrom,
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncWith,
                ast.Call,
                ast.Expr,
            ),
        ):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                nodes.append(node)

    return nodes


# ============================================================
# EXACT TEXT SEARCH
# ============================================================

def exact_text_matches(source: str, snippet: str):
    """
    Find exact occurrences of the RAG snippet in the original file.

    This is useful because AST matching can identify the correct
    code structure, while this gives us the exact character index.
    """

    matches = []

    start = 0

    while True:

        index = source.find(snippet, start)

        if index == -1:
            break

        matches.append(
            (
                index,
                index + len(snippet),
            )
        )

        start = index + 1

    return matches


# ============================================================
# AST SEARCH
# ============================================================

def find_with_ast(source: str, snippet: str):
    """
    Find a snippet using AST structure.

    Returns possible matches with character indexes.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [], f"Could not parse source file: {e}"

    snippet_fingerprint = ast_fingerprint(snippet)

    if snippet_fingerprint is None:
        return [], "Snippet is not independently parseable"

    candidates = []

    for node in collect_ast_nodes(tree):

        node_source = get_node_source(source, node)

        node_fingerprint = ast_fingerprint(node_source)

        if node_fingerprint == snippet_fingerprint:

            start, end = get_node_indexes(source, node)

            candidates.append(
                {
                    "node_type": type(node).__name__,
                    "start_character": start,
                    "end_character": end,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "code": node_source,
                }
            )

    return candidates, None


# ============================================================
# COMBINED SEARCH
# ============================================================

def find_code(source: str, snippet: str):
    """
    First try exact text matching.

    If exact matching fails, use AST matching.
    """

    # --------------------------------------------------------
    # 1. Exact match
    # --------------------------------------------------------

    exact_matches = exact_text_matches(source, snippet)

    if exact_matches:

        results = []

        for start, end in exact_matches:

            results.append(
                {
                    "method": "exact",
                    "start_character": start,
                    "end_character": end,
                    "code": source[start:end],
                }
            )

        return results

    # --------------------------------------------------------
    # 2. AST match
    # --------------------------------------------------------

    ast_matches, error = find_with_ast(source, snippet)

    if ast_matches:

        for match in ast_matches:
            match["method"] = "ast"

        return ast_matches

    return []


# ============================================================
# CHECK ONE SOURCE
# ============================================================

def check_source(source_info):
    """
    Check one source from the RAG dataset.
    """

    relative_path = source_info["file_path"]

    file_path = PROJECT_ROOT / relative_path

    expected_start = source_info.get("first_character_index")
    expected_end = source_info.get("last_character_index")

    print()
    print(f"{CYAN}{'=' * 100}{RESET}")
    print(f"{BOLD}{BLUE}FILE:{RESET} {relative_path}")

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not file_path.is_file():

        print(f"{BOLD}{RED}FILE NOT FOUND{RESET}")
        print(f"{RED}{file_path}{RESET}")

        return {
            "status": "missing_file",
            "file_path": relative_path,
        }

    print(f"{BOLD}{GREEN}FILE FOUND{RESET}")

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception as e:

        print(f"{RED}READ ERROR: {e}{RESET}")

        return {
            "status": "read_error",
            "file_path": relative_path,
        }

    # --------------------------------------------------------
    # Get expected RAG snippet
    # --------------------------------------------------------

    if expected_start is None or expected_end is None:

        print(
            f"{YELLOW}No character indexes in dataset{RESET}"
        )

        return {
            "status": "no_indexes",
            "file_path": relative_path,
        }

    expected_snippet = source[expected_start:expected_end]

    print(
        f"{BLUE}Dataset indexes:{RESET} "
        f"{expected_start} -> {expected_end}"
    )

    print(
        f"{BLUE}Snippet length:{RESET} "
        f"{len(expected_snippet)}"
    )

    # --------------------------------------------------------
    # Search the extracted snippet
    # --------------------------------------------------------

    matches = find_code(source, expected_snippet)

    if not matches:

        print(
            f"{BOLD}{RED}AST / TEXT MATCH: NOT FOUND{RESET}"
        )

        return {
            "status": "not_found",
            "file_path": relative_path,
            "expected_start": expected_start,
            "expected_end": expected_end,
        }

    # --------------------------------------------------------
    # Display matches
    # --------------------------------------------------------

    print(
        f"{BOLD}{GREEN}MATCH FOUND: {len(matches)}{RESET}"
    )

    for i, match in enumerate(matches, 1):

        print()
        print(
            f"{MAGENTA}Match #{i}{RESET}"
        )

        print(
            f"{GREEN}Method          :{RESET} "
            f"{match['method']}"
        )

        print(
            f"{GREEN}Start character :{RESET} "
            f"{match['start_character']}"
        )

        print(
            f"{GREEN}End character   :{RESET} "
            f"{match['end_character']}"
        )

        if "node_type" in match:

            print(
                f"{GREEN}AST node        :{RESET} "
                f"{match['node_type']}"
            )

        # ----------------------------------------------------
        # Compare with dataset indexes
        # ----------------------------------------------------

        if (
            match["start_character"] == expected_start
            and match["end_character"] == expected_end
        ):

            print(
                f"{BOLD}{GREEN}"
                "INDEX: EXACT MATCH"
                f"{RESET}"
            )

        else:

            print(
                f"{BOLD}{YELLOW}"
                "INDEX: DIFFERENT LOCATION"
                f"{RESET}"
            )

        # ----------------------------------------------------
        # Print code
        # ----------------------------------------------------

        print(
            f"{YELLOW}{'-' * 80}{RESET}"
        )

        print(match["code"][:1000])


    return {
        "status": "found",
        "file_path": relative_path,
        "expected_start": expected_start,
        "expected_end": expected_end,
        "matches": matches,
    }


# ============================================================
# MAIN DATASET CHECK
# ============================================================

def check_dataset():

    print(
        f"{BOLD}{CYAN}"
        "\nAST RAG SOURCE VALIDATOR"
        f"{RESET}"
    )

    print(
        f"{BLUE}Dataset:{RESET} {DATASET_FILE}"
    )

    print(
        f"{BLUE}Project root:{RESET} {PROJECT_ROOT}"
    )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    questions = dataset.get("rag_questions", [])

    print(
        f"{BLUE}Questions:{RESET} {len(questions)}"
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total = 0
    found = 0
    missing = 0
    exact = 0
    ast_found = 0

    # --------------------------------------------------------
    # Process questions
    # --------------------------------------------------------

    for question in questions:

        question_id = question.get("question_id")

        print()
        print(
            f"{BOLD}{CYAN}"
            f"QUESTION {question_id}"
            f"{RESET}"
        )

        for source in question.get("sources", []):

            total += 1

            result = check_source(source)

            if result["status"] == "missing_file":

                missing += 1

            elif result["status"] == "found":

                found += 1

                methods = {
                    match["method"]
                    for match in result["matches"]
                }

                if "exact" in methods:
                    exact += 1

                if "ast" in methods:
                    ast_found += 1

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print(
        f"{BOLD}{CYAN}"
        f"{'#' * 100}"
        f"{RESET}"
    )

    print(
        f"{BOLD}{YELLOW}"
        "FINAL SUMMARY"
        f"{RESET}"
    )

    print(
        f"{CYAN}{'#' * 100}{RESET}"
    )

    print(
        f"{BLUE}Total sources :{RESET} {total}"
    )

    print(
        f"{GREEN}Found         :{RESET} {found}"
    )

    print(
        f"{RED}Missing       :{RESET} {missing}"
    )

    print(
        f"{GREEN}Exact matches :{RESET} {exact}"
    )

    print(
        f"{MAGENTA}AST matches   :{RESET} {ast_found}"
    )

    print(
        f"{CYAN}{'#' * 100}{RESET}"
    )


if __name__ == "__main__":
    check_dataset()
