#!/usr/bin/env python3
"""
Safe PICO-8 Lua minifier for Ashen Edge.
Applies only transformations that reduce TOKEN COUNT:
  1. print(...) → ?...        (saves 2-3 tokens per call)
  2. Unnecessary semicolons   (saves 1 token each)

Does NOT do: variable renaming, block shorthand, assignment merging,
whitespace/comment stripping (those save chars, not tokens).
Reads ashen_edge.p8, writes ashen_edge_min.p8 (never overwrites source).
"""

import re, os, sys
from count_tokens import tokenize, count_tokens

DIR = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(DIR, "ashen_edge.p8")
DEST = os.path.join(DIR, "ashen_edge_min.p8")

TOKEN_LIMIT = 8192

# ── Transformations ───────────────────────────────────────────────────────────

def remove_semicolons(src):
    """Remove semicolons that aren't needed for statement separation.
    A semicolon is only required before '(' to prevent ambiguous function calls.
    """
    # Replace ; not followed by ( (with optional whitespace)
    src = re.sub(r';(\s*)(?!\()', r'\1', src)
    return src

def print_shorthand(src):
    """Replace print(...) with ?...  — saves 2 tokens per call.
    Only replaces standalone print() calls (not print as a value, e.g. x=print).
    """
    # Match: print( ... ) where parens are balanced
    # We do a simple pass: find 'print(' at a token boundary, then find matching ')'
    result = []
    i = 0
    while i < len(src):
        # Look for word-boundary 'print('
        m = re.match(r'print\s*\(', src[i:])
        # Make sure it's a standalone identifier (not part of longer word)
        if m and (i == 0 or not (src[i-1].isalnum() or src[i-1] == '_')):
            open_pos = i + m.end() - 1  # position of '('
            # Find matching closing paren
            depth = 1
            j = open_pos + 1
            in_str = False
            str_char = None
            while j < len(src) and depth > 0:
                c = src[j]
                if in_str:
                    if c == '\\':
                        j += 2
                        continue
                    if c == str_char:
                        in_str = False
                elif c in ('"', "'"):
                    in_str = True
                    str_char = c
                elif c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                j += 1
            if depth == 0:
                # Extract args (without outer parens)
                args = src[open_pos+1:j-1]
                result.append('?')
                result.append(args)
                i = j
                continue
        result.append(src[i])
        i += 1
    return ''.join(result)

# ── P8 file handling ──────────────────────────────────────────────────────────

def read_p8(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def split_p8(content):
    """Split .p8 into header + sections dict."""
    header_end = content.index('\n', content.index('pico-8')) + 1
    header = content[:header_end]
    sections = {}
    current = None
    buf = []
    for line in content[header_end:].splitlines(keepends=True):
        m = re.match(r'^(__\w+__)\n', line)
        if m:
            if current:
                sections[current] = ''.join(buf)
            current = m.group(1)
            buf = []
        else:
            buf.append(line)
    if current:
        sections[current] = ''.join(buf)
    return header, sections

def join_p8(header, sections):
    out = header
    for name, body in sections.items():
        out += f'{name}\n{body}'
    return out

# ── Main ──────────────────────────────────────────────────────────────────────

def bar(used, limit, width=30):
    filled = int(width * used / limit)
    pct = 100 * used / limit
    color = '\033[91m' if pct > 90 else ('\033[93m' if pct > 70 else '\033[92m')
    return f"{color}[{'█'*filled}{'░'*(width-filled)}]\033[0m {used:>5}/{limit} ({pct:.1f}%)"

def minify_lua(src):
    src = print_shorthand(src)
    src = remove_semicolons(src)
    return src

if __name__ == '__main__':
    if not os.path.exists(SRC):
        print(f"Source not found: {SRC}")
        sys.exit(1)

    content = read_p8(SRC)
    header, sections = split_p8(content)

    lua_orig = sections.get('__lua__', '')
    lua_min  = minify_lua(lua_orig)

    sections_min = dict(sections)
    sections_min['__lua__'] = lua_min

    t0 = count_tokens(tokenize(lua_orig))
    t1 = count_tokens(tokenize(lua_min))

    print(f"\n\033[1mMinifying {os.path.basename(SRC)}\033[0m")
    print(f"  before  {bar(t0, TOKEN_LIMIT)}")
    print(f"  after   {bar(t1, TOKEN_LIMIT)}")
    print(f"  saved   \033[1m{t0-t1:+d} tokens\033[0m")

    out = join_p8(header, sections_min)
    with open(DEST, 'w', encoding='utf-8') as f:
        f.write(out)
    print(f"\n  written → {os.path.basename(DEST)}\n")
