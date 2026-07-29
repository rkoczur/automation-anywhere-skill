#!/usr/bin/env python3
"""
A360_FLATTEN.py
---------------

Render an Automation Anywhere A360 TaskBot JSON as a human-readable,
one-line-per-action listing that mirrors the A360 web-editor view.

Usage
-----
    python3 A360_FLATTEN.py path/to/bot.json                 # writes ./<bot>.flat.txt + stdout
    python3 A360_FLATTEN.py path/to/bot.json -o out.txt      # custom output path
    python3 A360_FLATTEN.py path/to/bot.json --quiet         # no stdout, only file
    python3 A360_FLATTEN.py path/to/bot.json --max-str 60    # truncate long literals

Design notes
------------
* Line numbers match the A360 editor exactly: every command node counts as
  one line, and every branch header (else / elseIf / catch / finally) also
  counts as one line, in the depth-first order used by the editor.
* Nested commands are indented by 2 spaces per depth level.
* A dispatch table (PACKAGE, COMMAND) -> formatter handles known commands.
* Unknown commands fall back to a generic "Package: command k=v k=v" line
  so the script keeps working on new packages you haven't seen before.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Value rendering
# ---------------------------------------------------------------------------

def _quote(s: str) -> str:
    return '"' + s + '"'


_PURE_VAR_RE = re.compile(r"^\$[^$]+\$$")


def render_value(v: Any, max_str: Optional[int] = None) -> str:
    """Render an A360 value object as a short display string."""
    if v is None:
        return ""
    if not isinstance(v, dict):
        return str(v)

    t = v.get("type", "")

    # Expression form (variable interpolation / inline function)
    if "expression" in v and v["expression"] is not None:
        expr = v["expression"]
        # If it's a single-variable ref like "$foo$" -> bare $foo$
        # Otherwise, if it's a STRING/FILE, quote it (matches editor UI).
        if _PURE_VAR_RE.match(expr):
            out = expr
        elif t in ("STRING", "FILE"):
            out = _quote(expr)
        else:
            out = expr
        return _truncate(out, max_str)

    # Literal payloads
    if t == "STRING":
        return _truncate(_quote(v.get("string", "")), max_str)
    if t == "NUMBER":
        return v.get("number", "")
    if t == "BOOLEAN":
        return "True" if v.get("boolean") else "False"
    if t == "VARIABLE":
        return f'${v.get("variableName", "")}$'
    if t == "CREDENTIAL":
        c = v.get("credential", {}) or {}
        return f'[Credential {c.get("lockerName","?")}.{c.get("name","?")}.{c.get("attributeName","?")}]'
    if t == "FILE":
        return _truncate(_quote(v.get("string", "") or "<file>"), max_str)
    if t == "SESSION":
        return v.get("expression") or "<session>"
    if t == "EXCEPTION":
        return v.get("exceptionName", "<exception>")
    if t == "LIST":
        return "<list>"
    if t == "DICTIONARY":
        return "<dictionary>"
    if t == "TABLE":
        return "<table>"
    if t == "RECORD":
        return "<record>"

    # Fallback: compact JSON
    return _truncate(json.dumps(v, ensure_ascii=False), max_str)


def _truncate(s: str, max_str: Optional[int]) -> str:
    if max_str is None or len(s) <= max_str:
        return s
    return s[: max_str - 3] + "..."


def attr(node: dict, name: str) -> Optional[dict]:
    """Get attribute `name` (its .value) from a node's attributes list."""
    for a in node.get("attributes", []) or []:
        if a.get("name") == name:
            return a.get("value")
    return None


def attr_raw(node: dict, name: str) -> Optional[dict]:
    """Get the *raw* attribute object (including nested attributes/returnTo)."""
    for a in node.get("attributes", []) or []:
        if a.get("name") == name:
            return a
    return None


def return_var(node: dict) -> Optional[str]:
    r = node.get("returnTo")
    if isinstance(r, dict) and r.get("type") == "VARIABLE":
        return f'${r.get("variableName","")}$'
    return None


# ---------------------------------------------------------------------------
# Operator translation (used for `if` conditions)
# ---------------------------------------------------------------------------

_OPS = {
    "EQ": "=", "NEQ": "!=",
    "GT": ">", "GTE": ">=",
    "LT": "<", "LTE": "<=",
    "CONTAINS": "contains",
    "STARTS_WITH": "starts with",
    "ENDS_WITH": "ends with",
    "MATCHES_REGEX": "matches regex",
    "NOT_CONTAINS": "does not contain",
}


def render_condition(cond_attr: dict, max_str: Optional[int]) -> str:
    """Render an if/elseIf condition attribute as `<left> <op> <right>`."""
    if not cond_attr:
        return "<condition>"
    inner = cond_attr.get("attributes", []) or []
    parts = {a.get("name"): a.get("value") for a in inner}
    val = cond_attr.get("value", {}) or {}
    cname = val.get("conditionalName", "")

    # Boolean condition (single operand)
    if cname == "booleanVariable":
        v = parts.get("variable")
        return f'{render_value(v, max_str)} is True'

    # Two-operand comparisons (numberVariable, stringVariable, datetimeVariable, ...)
    left = render_value(parts.get("variable"), max_str)
    op_raw = (parts.get("operator") or {}).get("string", "?")
    op = _OPS.get(op_raw, op_raw)
    right = render_value(parts.get("value"), max_str)
    if left or right:
        return f"{left} {op} {right}".strip()
    return cname or "<condition>"


# ---------------------------------------------------------------------------
# Per-command formatters
# ---------------------------------------------------------------------------

# Each formatter has signature: (node, ctx) -> str
# ctx is a dict with: max_str, is_branch(bool), parent_cmd (for context if needed)

def fmt_comment(n, ctx):
    return f'Comment {render_value(attr(n, "comment"), ctx["max_str"])}'


def fmt_step(n, ctx):
    return f'Step {render_value(attr(n, "title"), ctx["max_str"])}'


def fmt_if(n, ctx):
    ca = attr_raw(n, "condition")
    return f'If {render_condition(ca, ctx["max_str"])}'


def fmt_else(n, ctx):
    return "Else"


def fmt_elseif(n, ctx):
    ca = attr_raw(n, "condition")
    return f'Else If {render_condition(ca, ctx["max_str"])}'


def fmt_try(n, ctx):
    return "Error handler: Try"


def fmt_catch(n, ctx):
    exc = attr(n, "exceptionType")
    exc_name = (exc or {}).get("exceptionName", "All errors")
    return f"Error handler: Catch {exc_name}"


def fmt_finally(n, ctx):
    return "Error handler: Finally"


def fmt_throw(n, ctx):
    msg = render_value(attr(n, "message"), ctx["max_str"])
    return f"Error handler: Throw {msg}"


def fmt_loop_start(n, ctx):
    it = attr_raw(n, "iterator")
    if not it:
        return "Loop"
    it_val = it.get("value", {}) or {}
    it_name = it_val.get("iteratorName", "")
    inner = {a.get("name"): a.get("value") for a in it.get("attributes", []) or []}
    counter = ""
    r = it.get("returnTo") or {}
    if r.get("type") == "VARIABLE":
        counter = f' -> ${r.get("variableName","")}$'
    if it_name == "loop.iterators.times":
        return f'Loop: {render_value(inner.get("times"), ctx["max_str"])} times{counter}'
    if it_name in ("loop.iterators.list", "loop.iterators.forEachItemInList"):
        src = render_value(inner.get("list") or inner.get("sourceList"), ctx["max_str"])
        return f"Loop: For each item in list {src}{counter}"
    if it_name in ("loop.iterators.dictionary", "loop.iterators.forEachItemInDictionary"):
        src = render_value(inner.get("dictionary") or inner.get("sourceDictionary"), ctx["max_str"])
        return f"Loop: For each item in dictionary {src}{counter}"
    if it_name and it_name.startswith("loop.iterators."):
        kind = it_name.split(".")[-1]
        return f"Loop: {kind}{counter}"
    return f"Loop{counter}"


def fmt_loop_break(n, ctx):
    a = render_value(attr(n, "anchor"), ctx["max_str"])
    # anchor comes as STRING "ConnectRetry" -> already quoted; unquote for readability
    a_clean = a.strip('"')
    return f"Loop: Break &{a_clean}" if a_clean else "Loop: Break"


def fmt_loop_continue(n, ctx):
    a = render_value(attr(n, "anchor"), ctx["max_str"])
    a_clean = a.strip('"')
    return f"Loop: Continue &{a_clean}" if a_clean else "Loop: Continue"


def fmt_string_assign(n, ctx):
    src = render_value(attr(n, "sourceString"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"String: Assign {src} to {dest}"


def fmt_boolean_assign(n, ctx):
    # Boolean.assign uses source=constant/variable + userDefined
    src = attr(n, "source")
    ud = attr(n, "userDefined")
    if src and (src.get("string") == "constant") and ud:
        raw = ud.get("string", "")
        val = "True" if raw.lower() == "true" else ("False" if raw.lower() == "false" else raw)
    else:
        val = render_value(ud or src, ctx["max_str"])
    dest = return_var(n) or "?"
    return f"Boolean: Assign {val} to {dest}"


def fmt_file_assign(n, ctx):
    src = render_value(attr(n, "sourceFile"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"File: Assign {src} to {dest}"


def fmt_number_assign_to(n, ctx):
    src = render_value(attr(n, "input"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"Number: Assign {src} to {dest}"


def fmt_number_to_string(n, ctx):
    src = render_value(attr(n, "input"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"Number: Convert {src} to string and assign to {dest}"


def fmt_datetime_to_string(n, ctx):
    src = render_value(attr(n, "source"), ctx["max_str"])
    pat = render_value(attr(n, "patternInput"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"Datetime: Format {src} as {pat} and assign to {dest}"


def fmt_string_replace(n, ctx):
    src = render_value(attr(n, "sourceString"), ctx["max_str"])
    find = render_value(attr(n, "find"), ctx["max_str"])
    repl = render_value(attr(n, "replaceWith"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"String: Replace {find} with {repl} in {src} and assign the result to {dest}"


def fmt_string_random(n, ctx):
    ln = render_value(attr(n, "randomStringLength"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"String: Random string of length {ln} and assign to {dest}"


def fmt_system_info(n, ctx):
    field = render_value(attr(n, "systemNameByText"), ctx["max_str"])
    dest = return_var(n) or "?"
    return f"System: Get {field} and assign to {dest}"


def fmt_create_folder(n, ctx):
    p = render_value(attr(n, "folderPath"), ctx["max_str"])
    return f"Folder: Create {p}"


def fmt_add_item(n, ctx):
    lst = render_value(attr(n, "sourceList"), ctx["max_str"])
    item = render_value(attr(n, "listItem"), ctx["max_str"])
    return f"List: Add {item} to {lst}"


def fmt_log_to_file(n, ctx):
    path = render_value(attr(n, "filePath"), ctx["max_str"])
    content = render_value(attr(n, "logContent"), ctx["max_str"])
    opt = (attr(n, "logOption") or {}).get("string", "APPEND_FILE")
    verb = "Append to" if opt == "APPEND_FILE" else "Write to"
    return f"Log to file: {verb} {path}: {content}"


def fmt_capture_desktop(n, ctx):
    p = render_value(attr(n, "filePath"), ctx["max_str"])
    return f"Screen: Capture desktop to {p}"


def fmt_outlook_connect(n, ctx):
    return "Microsoft 365 Outlook: Connect"


def fmt_outlook_disconnect(n, ctx):
    s = render_value(attr(n, "sessionName"), ctx["max_str"])
    return f"Microsoft 365 Outlook: Disconnect {s}".rstrip()


def fmt_outlook_send(n, ctx):
    to = render_value(attr(n, "toRecipients"), ctx["max_str"])
    subj = render_value(attr(n, "subject"), ctx["max_str"])
    return f"Microsoft 365 Outlook: Send email to {to} - Subject: {subj}"


def fmt_run_task(n, ctx):
    tv = attr(n, "taskbot") or {}
    tf = (tv.get("taskbotFile") or {}).get("string", "")
    # Extract just the bot name from the repository path
    bot_name = tf.rsplit("/", 1)[-1] if tf else "?"
    # A360 encodes spaces as %20
    bot_name = bot_name.replace("%20", " ")
    return f"Task Bot: Run {bot_name} and assign output to variable"


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

FORMATTERS: dict[tuple[str, str], Callable] = {
    ("Comment", "Comment"): fmt_comment,
    ("Step", "step"): fmt_step,

    ("If", "if"): fmt_if,
    ("If", "else"): fmt_else,
    ("If", "elseIf"): fmt_elseif,

    ("ErrorHandler", "try"): fmt_try,
    ("ErrorHandler", "catch"): fmt_catch,
    ("ErrorHandler", "finally"): fmt_finally,
    ("ErrorHandler", "throw"): fmt_throw,

    ("Loop", "loop.commands.start"): fmt_loop_start,
    ("Loop", "loop.commands.break"): fmt_loop_break,
    ("Loop", "loop.commands.continue"): fmt_loop_continue,

    ("String", "assign"): fmt_string_assign,
    ("String", "replace"): fmt_string_replace,
    ("String", "randomString"): fmt_string_random,

    ("Boolean", "assign"): fmt_boolean_assign,
    ("File", "assign"): fmt_file_assign,

    ("Number", "assignToNumber"): fmt_number_assign_to,
    ("Number", "toString"): fmt_number_to_string,
    ("Datetime", "toString"): fmt_datetime_to_string,

    ("System", "systemInformation"): fmt_system_info,
    ("Folder", "createFolder"): fmt_create_folder,
    ("List", "addItem"): fmt_add_item,
    ("LogToFile", "logToFile"): fmt_log_to_file,
    ("Screen", "captureDesktop"): fmt_capture_desktop,

    ("Microsoft 365 Outlook", "Connect"): fmt_outlook_connect,
    ("Microsoft 365 Outlook", "Disconnect"): fmt_outlook_disconnect,
    ("Microsoft 365 Outlook", "Send"): fmt_outlook_send,

    ("TaskBot", "runTask"): fmt_run_task,
}


def fmt_generic(n, ctx):
    """Fallback formatter used when a (package, command) pair is unknown."""
    pkg = n.get("packageName", "")
    cmd = n.get("commandName", "")
    bits = []
    for a in n.get("attributes", []) or []:
        name = a.get("name")
        val = render_value(a.get("value"), ctx["max_str"])
        if val:
            bits.append(f"{name}={val}")
    dest = return_var(n)
    tail = f" -> {dest}" if dest else ""
    joined = ", ".join(bits)
    return f"{pkg}: {cmd}" + (f" [{joined}]" if joined else "") + tail


def format_node(n, ctx) -> str:
    key = (n.get("packageName", ""), n.get("commandName", ""))
    fmt = FORMATTERS.get(key, fmt_generic)
    try:
        text = fmt(n, ctx)
    except Exception as e:  # never crash on a single weird node
        text = f"[!] {n.get('packageName','')}.{n.get('commandName','')} (render error: {e})"
    if n.get("disabled"):
        text = f"[disabled] {text}"
    return text


# ---------------------------------------------------------------------------
# Tree walk with editor-accurate line numbering
# ---------------------------------------------------------------------------

def walk(nodes, depth, ctx, out):
    """Depth-first walk that counts each node and each branch header as one line."""
    for n in nodes:
        ctx["line"] += 1
        out.append((ctx["line"], depth, format_node(n, ctx)))

        # Nested statements
        children = n.get("children") or []
        if children:
            walk(children, depth + 1, ctx, out)

        # else / catch / finally / elseIf branches
        for b in n.get("branches") or []:
            ctx["line"] += 1
            out.append((ctx["line"], depth, format_node(b, ctx)))
            b_children = b.get("children") or []
            if b_children:
                walk(b_children, depth + 1, ctx, out)


def flatten_bot(bot_json: dict, max_str: Optional[int] = None) -> list[tuple[int, int, str]]:
    ctx = {"line": 0, "max_str": max_str}
    out: list[tuple[int, int, str]] = []
    walk(bot_json.get("nodes") or [], 0, ctx, out)
    return out


def render_listing(lines: list[tuple[int, int, str]], indent: int = 2) -> str:
    if not lines:
        return "(empty bot)\n"
    width = max(3, len(str(lines[-1][0])))
    rows = []
    for ln, depth, text in lines:
        rows.append(f"{ln:>{width}}  {' ' * (indent * depth)}{text}")
    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render an A360 TaskBot JSON as a one-line-per-action listing."
    )
    ap.add_argument("input", help="Path to bot .json file")
    ap.add_argument("-o", "--output", help="Output file (default: <input>.flat.txt)")
    ap.add_argument("--max-str", type=int, default=None,
                    help="Truncate string/expression values longer than N chars")
    ap.add_argument("--indent", type=int, default=2,
                    help="Spaces per nesting level (default: 2)")
    ap.add_argument("--quiet", action="store_true", help="Do not print to stdout")
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        bot = json.load(fh)

    lines = flatten_bot(bot, max_str=args.max_str)
    text = render_listing(lines, indent=args.indent)

    out_path = args.output
    if not out_path:
        base = os.path.splitext(os.path.basename(args.input))[0]
        out_path = f"./{base}.flat.txt"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    if not args.quiet:
        sys.stdout.write(text)

    sys.stderr.write(f"[A360_FLATTEN] {len(lines)} lines written to {out_path}\n")


if __name__ == "__main__":
    main()
