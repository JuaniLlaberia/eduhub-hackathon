"""
Grounding guardrail: every number in a user-facing text must come from the computed evidence.
Numbers are compared as canonical es-AR tokens: "2,1%", "1,4x", "21 h", "3386" (thousands dots removed).
"""
import re

SMALL_INT_MAX = 7
NUMBER_PATTERN = re.compile(
    r"(?<![\w.,@#])"
    r"(?P<num>\d{1,3}(?:\.\d{3})+|\d+(?:,\d+)?)"
    r"(?:\s?(?P<unit>%|×|x\b|hs?\b))?"
)
UNITS = {"%": "%", "×": "x", "x": "x", "h": " h", "hs": " h"}

def extract_numbers(text: str) -> set[str]:
    """
    Return the canonical number tokens in text (percentages, multipliers, hours, plain numbers).
    """
    tokens = set()
    for match in NUMBER_PATTERN.finditer(text):
        number = match["num"].replace(".", "")
        unit = UNITS.get(match["unit"] or "", "")
        tokens.add(f"{number}{unit}")
    return tokens

def numeric_part(token: str) -> str:
    """
    The number of a token without its unit ("21 h" -> "21", "1,4x" -> "1,4").
    """
    return token.removesuffix(" h").removesuffix("%").removesuffix("x")

def ungrounded(text: str, allowed: set[str]) -> set[str]:
    """
    Return the numbers in text that are not in allowed. A bare number is fine if it is a small integer
    (<= 7, e.g. weekdays or list numbering) or the number of an allowed token ("21" when "21 h" is allowed).
    """
    allowed_bare = {numeric_part(token) for token in allowed}
    missing = set()
    for token in extract_numbers(text):
        if token in allowed:
            continue
        is_bare = numeric_part(token) == token
        if is_bare and (token in allowed_bare or (token.isdigit() and int(token) <= SMALL_INT_MAX)):
            continue
        missing.add(token)
    return missing
