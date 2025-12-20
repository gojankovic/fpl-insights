import json
import shutil
import re
from typing import Dict, Any
from textwrap import TextWrapper
from colorama import Fore, Style

# ANSI COLORS
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

TERM_WIDTH = shutil.get_terminal_size((80, 20)).columns
MAX_WIDTH = min(78, TERM_WIDTH - 2)


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r'(?<=\w)\s*\n\s*(?=\w)', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)

    return text


def wrap_text(text: str, indent: int = 6) -> str:
    text = normalize_text(text)

    wrapper = TextWrapper(
        width=MAX_WIDTH - indent,
        break_long_words=False,
        break_on_hyphens=False
    )

    pad = " " * indent
    return "\n".join(pad + line for line in wrapper.wrap(text))


def header(title: str) -> str:
    bar = "━" * MAX_WIDTH
    return f"{YELLOW}{bar}\n {title}\n{bar}{RESET}"


def print_pretty_transfer(result: dict):
    if result.get("error"):
        print(f"{RED}[ERROR]{RESET} {result['error']}\n")
        if "raw" in result:
            print(json.dumps(result["raw"], indent=2, ensure_ascii=False))
        return

    data = result["json"]

    print(header(f"FPLInsights Transfer Advisor – GW{data.get('gameweek', '?')}"))
    print()

    for t in data.get("suggested_transfers", []):
        print(f"{RED}  OUT  {RESET}{t.get('out_name', 'Unknown')}")
        print(f"{GREEN}  IN   {RESET}{t.get('in_name', 'Unknown')}")

        if t.get("reason"):
            print(wrap_text(t["reason"]))
        print()

    print(f"{CYAN}  Hit cost:{RESET} {data.get('hit_cost', 0)}\n")

    if data.get("rationale"):
        print(f"{CYAN}  Rationale:{RESET}")
        print(wrap_text(data["rationale"]))
        print()

    print(header(""))


def print_captaincy_output(data: Dict[str, Any]):
    line = "─" * min(TERM_WIDTH, 80)

    print(Fore.YELLOW + f"\nFPLInsights Captaincy Advisor – GW{data['gameweek']}" + Style.RESET_ALL)
    print(Fore.YELLOW + line + Style.RESET_ALL)

    cap = data["suggested_captain"]
    print(Fore.GREEN + "\nCAPTAIN" + Style.RESET_ALL)
    print(Fore.CYAN + f"  {cap['name']} (ID {cap['id']})" + Style.RESET_ALL)
    print(wrap_text(cap["reason"], indent=2))

    vc = data["suggested_vice_captain"]
    print(Fore.GREEN + "\nVICE-CAPTAIN" + Style.RESET_ALL)
    print(Fore.BLUE + f"  {vc['name']} (ID {vc['id']})" + Style.RESET_ALL)
    print(wrap_text(vc["reason"], indent=2))

    print(Fore.MAGENTA + "\nOther viable options:" + Style.RESET_ALL)
    for o in data.get("other_viable_options", []):
        print(f"  • {o['name']} (ID {o['id']})")
        print(wrap_text(o["reason"], indent=4))

    if data.get("notes"):
        print(Fore.YELLOW + "\nNotes:" + Style.RESET_ALL)
        print(wrap_text(data["notes"], indent=2))

    print(Fore.YELLOW + line + Style.RESET_ALL + "\n")
