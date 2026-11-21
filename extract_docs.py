import json
from pathlib import Path


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"


# ============================================================
# PATHS
# ============================================================

DATASET_FILE = Path(
    "/home/ybaddi/RAG/data/datasets_public/public/AnsweredQuestions/dataset_docs_public.json"
)

PROJECT_ROOT = Path("/home/ybaddi/RAG")


# ============================================================
# CHECK DATASET
# ============================================================

def check_docs():

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("rag_questions", [])

    total_sources = 0
    files_found = 0
    files_missing = 0
    valid_indexes = 0
    invalid_indexes = 0

    print()
    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")
    print(f"{BOLD}{CYAN}Checking Documentation Dataset{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")

    for item in questions:

        question_id = item.get("question_id")
        question = item.get("question", "")

        for source in item.get("sources", []):

            total_sources += 1

            relative_path = source.get("file_path")
            first = source.get("first_character_index")
            last = source.get("last_character_index")

            file_path = PROJECT_ROOT / relative_path

            print()
            print(f"{CYAN}{'-' * 100}{RESET}")

            print(
                f"{BOLD}{BLUE}Question ID:{RESET} {question_id}"
            )

            print(
                f"{BOLD}{BLUE}Question:{RESET} {question}"
            )

            print(
                f"{BOLD}{BLUE}File:{RESET} {relative_path}"
            )

            # =================================================
            # CHECK FILE
            # =================================================

            if not file_path.is_file():

                files_missing += 1

                print(
                    f"{BOLD}{RED}✗ FILE NOT FOUND{RESET}"
                )

                print(
                    f"{RED}Expected path: {file_path}{RESET}"
                )

                continue

            files_found += 1

            print(
                f"{BOLD}{GREEN}✓ FILE FOUND{RESET}"
            )

            # =================================================
            # READ FILE
            # =================================================

            try:

                text = file_path.read_text(
                    encoding="utf-8"
                )

            except Exception as e:

                print(
                    f"{BOLD}{RED}✗ ERROR READING FILE{RESET}"
                )

                print(f"{RED}{e}{RESET}")

                continue

            file_length = len(text)

            print(
                f"{BOLD}{BLUE}File length:{RESET} {file_length}"
            )

            print(
                f"{BOLD}{BLUE}Character range:{RESET} "
                f"{first} -> {last}"
            )

            # =================================================
            # CHECK CHARACTER INDEXES
            # =================================================

            if (
                first is not None
                and last is not None
                and 0 <= first <= last <= file_length
            ):

                valid_indexes += 1

                print(
                    f"{BOLD}{GREEN}✓ CHARACTER INDEXES VALID{RESET}"
                )

                # Extract referenced documentation
                snippet = text[first:last]

                print()
                print(
                    f"{BOLD}{YELLOW}Referenced Documentation:{RESET}"
                )

                print(
                    f"{YELLOW}{'-' * 80}{RESET}"
                )

                print(snippet[:1500])

                if len(snippet) > 1500:
                    print(
                        f"{YELLOW}... [truncated]{RESET}"
                    )

            else:

                invalid_indexes += 1

                print(
                    f"{BOLD}{RED}✗ CHARACTER INDEXES INVALID{RESET}"
                )

    # ============================================================
    # SUMMARY
    # ============================================================

    print()
    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")
    print(f"{BOLD}{YELLOW}SUMMARY{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")

    print(
        f"{BLUE}Questions             :{RESET} {len(questions)}"
    )

    print(
        f"{BLUE}Total sources         :{RESET} {total_sources}"
    )

    print(
        f"{GREEN}Files found           :{RESET} {files_found}"
    )

    print(
        f"{RED}Files missing         :{RESET} {files_missing}"
    )

    print(
        f"{GREEN}Valid indexes         :{RESET} {valid_indexes}"
    )

    print(
        f"{RED}Invalid indexes       :{RESET} {invalid_indexes}"
    )

    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")

    # ============================================================
    # FINAL RESULT
    # ============================================================

    if files_missing == 0 and invalid_indexes == 0:

        print(
            f"{BOLD}{GREEN}"
            f"✓ ALL DOCUMENTATION SOURCES ARE VALID"
            f"{RESET}"
        )

    else:

        print(
            f"{BOLD}{RED}"
            f"✗ SOME DOCUMENTATION SOURCES HAVE PROBLEMS"
            f"{RESET}"
        )

    print(f"{BOLD}{CYAN}{'=' * 100}{RESET}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    check_docs()
