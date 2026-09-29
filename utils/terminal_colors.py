"""
ANSI color helpers for terminal print() output ONLY.
"""
RESET = "\033[0m"
BOLD = "\033[1m"

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"
_GRAY = "\033[90m"


def green(text):   return f"{_GREEN}{text}{RESET}"      # success (sent)
def red(text):      return f"{_RED}{text}{RESET}"        # failure
def yellow(text):   return f"{_YELLOW}{text}{RESET}"      # pending/batched
def blue(text):     return f"{BOLD}{_BLUE}{text}{RESET}"  # section headers
def cyan(text):     return f"{_CYAN}{text}{RESET}"        # dry-run / immediate
def magenta(text):  return f"{_MAGENTA}{text}{RESET}"     # scheduled batch/digest
def gray(text):     return f"{_GRAY}{text}{RESET}"        # skipped / no-op