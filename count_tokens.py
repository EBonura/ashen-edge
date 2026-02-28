#!/usr/bin/env python3
"""
PICO-8 token counter for .p8 and .lua files.
Token counting rules ported from shrinko8 (thisismypassport/shrinko8).

What counts as a token:
  - Identifiers, keywords, numbers, strings, operators, opening brackets
  - NOT: , . : ; :: ) ] } end local
  - NOT: unary - or ~ immediately before a number (no space, not after a value)
"""

import re, sys, os, zlib

# ── Tokenizer ────────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(
    r'(?s)'
    r'(--\[\[.*?\]\]'              # long comment
    r'|--[^\n]*'                   # line comment
    r'|\[\[.*?\]\]'                # long string
    r'|0[xX][0-9a-fA-F]*\.?[0-9a-fA-F]*(?:[pP][+-]?[0-9]+)?'  # hex number
    r'|0[bB][01]+'                 # binary number
    r'|[0-9]+\.?[0-9]*(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?'       # decimal number
    r'|\.[0-9]+(?:[eE][+-]?[0-9]+)?'                            # .5 style number
    r'|"(?:[^"\\]|\\.)*"'          # double-quoted string
    r"|'(?:[^'\\]|\\.)*'"          # single-quoted string
    r'|!='                         # != (alias for ~=)
    r'|<<=|>>='                    # compound shift-assign
    r'|<<[<>]?|>>[<>]?'           # shifts
    r'|[+\-*/%^&|~]=?'            # arith/bitwise (possibly =)
    r'|[<>]=?|[=~]='              # comparison
    r'|\.\.\.|\.{1,2}'            # ... .. .
    r'|[(){}\[\];:,#@\\]'         # punctuation
    r'|[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*'  # identifier / keyword
    r'|\S'                         # catch-all
    r')'
)

KEYWORDS = {
    'and','break','do','else','elseif','end','false','for','function',
    'goto','if','in','local','nil','not','or','repeat','return','then',
    'true','until','while',
    # PICO-8 extensions
    'poke','peek','poke2','peek2','poke4','peek4',
}

# Not counted
EXCLUDED = {',', '.', ':', ';', '::', ')', ']', '}', 'end', 'local'}

# Tokens that represent a "value" (unary - after these is binary, not unary)
VALUE_TYPES = {'number', 'string', 'ident'}
VALUE_ENDS  = {')', ']', '}', ';', 'end'}

def classify(tok):
    if re.fullmatch(r'(?:0[xX][0-9a-fA-F.]+(?:[pP][+-]?\d+)?|0[bB][01]+|\d[\d.]*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)', tok):
        return 'number'
    if tok.startswith('"') or tok.startswith("'") or tok.startswith('[['):
        return 'string'
    if re.fullmatch(r'[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*', tok):
        return 'ident'
    return 'punct'

def tokenize(src):
    """Return list of (tok_str, type, char_offset) skipping comments/whitespace."""
    tokens = []
    for m in TOKEN_RE.finditer(src):
        tok = m.group(0)
        if tok.startswith('--') or (tok.startswith('[[') and not tokens):
            continue  # comment
        typ = classify(tok)
        tokens.append((tok, typ, m.start()))
    return tokens

def count_tokens(tokens):
    count = 0
    for i, (tok, typ, pos) in enumerate(tokens):
        if tok in EXCLUDED:
            continue
        # unary - or ~ immediately before a number
        if tok in ('-', '~'):
            if i + 1 < len(tokens):
                ntok, ntyp, npos = tokens[i + 1]
                if ntyp == 'number' and npos == pos + len(tok):
                    # check previous token is not a value
                    if i > 0:
                        ptok, ptyp, _ = tokens[i - 1]
                        if ptyp not in VALUE_TYPES and ptok not in VALUE_ENDS:
                            continue
                    else:
                        continue  # first token, definitely unary
        count += 1
    return count

# ── File parsing ──────────────────────────────────────────────────────────────

def extract_lua(path):
    """Extract Lua section from .p8 or return raw content for .lua."""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    if path.endswith('.p8'):
        m = re.search(r'__lua__\n(.*?)(?=\n__\w+__|$)', content, re.DOTALL)
        return m.group(1) if m else ''
    return content

def compressed_size(lua_src):
    """Rough compressed byte estimate using zlib (PICO-8 uses a custom compressor)."""
    return len(zlib.compress(lua_src.encode('utf-8'), level=9))

# ── Main ──────────────────────────────────────────────────────────────────────

TOKEN_LIMIT      = 8192
CHAR_LIMIT       = 65535
COMPRESSED_LIMIT = 15616

def analyze(path):
    src = extract_lua(path)
    tokens = tokenize(src)
    ntok   = count_tokens(tokens)
    nchar  = len(src)
    ncomp  = compressed_size(src)

    def bar(used, limit, width=30):
        filled = int(width * used / limit)
        pct = 100 * used / limit
        color = '\033[91m' if pct > 90 else ('\033[93m' if pct > 70 else '\033[92m')
        return f"{color}[{'█'*filled}{'░'*(width-filled)}]\033[0m {used:>5}/{limit} ({pct:.1f}%)"

    print(f"\n\033[1m{os.path.basename(path)}\033[0m")
    print(f"  tokens     {bar(ntok,   TOKEN_LIMIT)}")
    print(f"  chars      {bar(nchar,  CHAR_LIMIT)}")
    print(f"  compressed {bar(ncomp,  COMPRESSED_LIMIT)}  (zlib estimate)")
    print()
    return ntok

if __name__ == '__main__':
    paths = sys.argv[1:] or [
        os.path.join(os.path.dirname(__file__), 'ashen_edge.p8'),
        os.path.join(os.path.dirname(__file__), 'ashen_edge.lua'),
    ]
    for p in paths:
        if os.path.exists(p):
            analyze(p)
            break
    else:
        print("Usage: python3 count_tokens.py [file.p8 | file.lua]")
