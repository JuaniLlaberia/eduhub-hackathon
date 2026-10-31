"""
House style checker for Python (ruff cannot express these rules):

1. Every function and class has a docstring formatted as: opening triple quotes alone on a line, text, closing alone.
2. Every function argument and return value has a type hint.
3. No blank line between a docstring and the first line of code of its function/class.
4. Exactly one blank line between functions/classes and their neighbours (never zero, never two).
5. Never two consecutive blank lines anywhere.

Rules 1-2 are skipped for test files. Usage: python scripts/check_style.py [paths...] (default: src/ and scripts/).
"""
from __future__ import annotations
import ast
import io
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("src/shared", "src/backend", "src/ai", "scripts")
SKIP_DIRS = {".venv", "node_modules", "__pycache__", "frontend", ".git"}
Definition = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

def is_test_file(path: Path) -> bool:
    """
    Return True for pytest files, which are exempt from the docstring and type-hint rules.
    """
    return path.name.startswith("test_") or path.name == "conftest.py" or "tests" in path.parts

def start_line(node: ast.stmt) -> int:
    """
    Return the first line of a statement, including its decorators.
    """
    decorators = getattr(node, "decorator_list", [])
    return min([node.lineno, *(d.lineno for d in decorators)])

def string_lines(source: str) -> set[int]:
    """
    Return the line numbers that are inside multi-line string literals (blank lines there are allowed).
    """
    lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.STRING and token.end[0] > token.start[0]:
            lines.update(range(token.start[0] + 1, token.end[0] + 1))
    return lines

def blank_lines_between(lines: list[str], end: int, start: int) -> int:
    """
    Count blank lines strictly between line end and line start (1-based, comments are not blank).
    """
    return sum(1 for line in lines[end:start - 1] if not line.strip())

def docstring_node(node: ast.AST) -> ast.Expr | None:
    """
    Return the docstring expression of a function/class, or None.
    """
    body = getattr(node, "body", [])
    first = body[0] if body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return first
    return None

def check_docstring(node: ast.AST, lines: list[str], errors: list[str], path: Path, test: bool) -> None:
    """
    Check presence and format of a definition's docstring and the absence of a blank line after it.
    """
    doc = docstring_node(node)
    name = getattr(node, "name", "?")
    if doc is None:
        if not test:
            errors.append(f"{path}:{node.lineno}: '{name}' has no docstring")
        return
    opening = lines[doc.lineno - 1].strip()
    closing = lines[doc.end_lineno - 1].strip()
    if opening != '"""' or closing != '"""' or doc.end_lineno - doc.lineno < 2:
        errors.append(f"{path}:{doc.lineno}: '{name}' docstring must be: \"\"\" / text / \"\"\" on separate lines")
    body = node.body
    if len(body) > 1 and blank_lines_between(lines, doc.end_lineno, start_line(body[1])) != 0:
        errors.append(f"{path}:{doc.end_lineno + 1}: no blank line allowed after the docstring of '{name}'")

def check_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool, errors: list[str],
                      path: Path) -> None:
    """
    Check that every argument (except self/cls) and the return value are annotated.
    """
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if is_method and args and args[0].arg in {"self", "cls"}:
        args = args[1:]
    for extra in (node.args.vararg, node.args.kwarg):
        if extra is not None:
            args.append(extra)
    for arg in args:
        if arg.annotation is None:
            errors.append(f"{path}:{node.lineno}: argument '{arg.arg}' of '{node.name}' has no type hint")
    if node.returns is None:
        errors.append(f"{path}:{node.lineno}: '{node.name}' has no return type hint")

def check_body_spacing(body: list[ast.stmt], lines: list[str], errors: list[str], path: Path,
                       has_docstring: bool) -> None:
    """
    Check exactly one blank line around every function/class inside a body.
    """
    for index in range(1, len(body)):
        previous, current = body[index - 1], body[index]
        if index == 1 and has_docstring:
            continue
        if isinstance(previous, Definition) or isinstance(current, Definition):
            blanks = blank_lines_between(lines, previous.end_lineno, start_line(current))
            if blanks != 1:
                errors.append(f"{path}:{start_line(current)}: expected exactly 1 blank line here, found {blanks}")

def check_file(path: Path) -> list[str]:
    """
    Return every style error found in one Python file.
    """
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [f"{path}:{error.lineno}: syntax error: {error.msg}"]
    test = is_test_file(path)
    check_body_spacing(tree.body, lines, errors, path, docstring_node(tree) is not None)
    for parent in ast.walk(tree):
        body = getattr(parent, "body", [])
        for child in body if isinstance(body, list) else []:
            if not isinstance(child, Definition):
                continue
            check_docstring(child, lines, errors, path, test)
            check_body_spacing(child.body, lines, errors, path, docstring_node(child) is not None)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not test:
                check_annotations(child, isinstance(parent, ast.ClassDef), errors, path)
    inside_strings = string_lines(source)
    for number in range(2, len(lines) + 1):
        if not lines[number - 1].strip() and not lines[number - 2].strip() and number not in inside_strings:
            errors.append(f"{path}:{number}: two consecutive blank lines")
    return sorted(set(errors), key=lambda e: (e.split(":")[0], int(e.split(":")[1])))

def collect(paths: list[str]) -> list[Path]:
    """
    Expand files and directories into the Python files to check.
    """
    files: list[Path] = []
    for raw in paths:
        path = (ROOT / raw) if not Path(raw).is_absolute() else Path(raw)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*.py") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))
    return sorted(set(files))

def main() -> None:
    """
    Check the given paths (default: all Python code) and exit 1 on any error.
    """
    files = collect(sys.argv[1:] or list(DEFAULT_PATHS))
    errors = [error for path in files for error in check_file(path)]
    for error in errors:
        print(error.replace(str(ROOT) + "/", ""))
    if errors:
        print(f"\n{len(errors)} style error(s). See docs/workflow.md §4.", file=sys.stderr)
        sys.exit(1)
    print(f"style OK ({len(files)} files)")

if __name__ == "__main__":
    main()
