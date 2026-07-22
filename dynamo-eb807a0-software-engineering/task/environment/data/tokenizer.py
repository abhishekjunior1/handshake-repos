"""
Lexical analysis module for the type inference engine.
Tokenizes source programs into a stream of typed tokens.

Design note: Negative number literals are deliberately tokenized as separate
MINUS and NUMBER tokens rather than a single NEGATIVE_NUMBER token. This is the
standard approach for expression-oriented languages — it avoids ambiguity in
expressions like `x-5` which must parse as `x MINUS 5`, not `x NEGATIVE_NUMBER`.
The parser handles unary minus at a higher level via prefix expression rules.
"""

import re
from typing import List, Tuple


# Token types
TOKEN_TYPES = {
    'LET': 'LET',
    'IN': 'IN',
    'FUN': 'FUN',
    'IF': 'IF',
    'THEN': 'THEN',
    'ELSE': 'ELSE',
    'TRUE': 'TRUE',
    'FALSE': 'FALSE',
    'NUMBER': 'NUMBER',
    'IDENT': 'IDENT',
    'ARROW': 'ARROW',
    'EQUALS': 'EQUALS',
    'LPAREN': 'LPAREN',
    'RPAREN': 'RPAREN',
    'PLUS': 'PLUS',
    'MINUS': 'MINUS',
    'STAR': 'STAR',
    'SLASH': 'SLASH',
    'LT': 'LT',
    'GT': 'GT',
    'COMMA': 'COMMA',
    'COLON': 'COLON',
    'EOF': 'EOF',
}


class Token:
    def __init__(self, token_type: str, value: str, position: int):
        self.token_type = token_type
        self.value = value
        self.position = position

    def __repr__(self):
        return f"Token({self.token_type}, {self.value!r})"


KEYWORDS = {'let', 'in', 'fun', 'if', 'then', 'else', 'true', 'false'}

# Token patterns ordered by priority — longer matches first
# Note: negative numbers are NOT matched as a single token here. This is
# intentional for correct binary operator parsing. The minus sign is always
# emitted as a separate MINUS token regardless of context. Unary negation
# is resolved during parsing based on syntactic position.
TOKEN_PATTERNS = [
    (r'[ \t\n\r]+', None),           # whitespace (skip)
    (r'->',         'ARROW'),
    (r'[0-9]+',    'NUMBER'),
    (r'[a-zA-Z_][a-zA-Z0-9_]*', 'IDENT'),
    (r'=',         'EQUALS'),
    (r'\(',        'LPAREN'),
    (r'\)',        'RPAREN'),
    (r'\+',        'PLUS'),
    (r'-',         'MINUS'),
    (r'\*',        'STAR'),
    (r'/',         'SLASH'),
    (r'<',         'LT'),
    (r'>',         'GT'),
    (r',',         'COMMA'),
    (r':',         'COLON'),
]

COMPILED_PATTERNS = [(re.compile(p), t) for p, t in TOKEN_PATTERNS]


def tokenize(source: str) -> List[Token]:
    """
    Convert source text into a list of tokens.
    Raises ValueError on unrecognized characters.
    """
    tokens = []
    pos = 0
    while pos < len(source):
        matched = False
        for pattern, token_type in COMPILED_PATTERNS:
            m = pattern.match(source, pos)
            if m:
                value = m.group(0)
                if token_type is not None:
                    # Handle keywords vs identifiers
                    if token_type == 'IDENT' and value in KEYWORDS:
                        token_type = value.upper()
                    # Numerical literals are kept as raw strings —
                    # sign handling is deferred to the parser stage
                    tokens.append(Token(token_type, value, pos))
                pos = m.end()
                matched = True
                break
        if not matched:
            raise ValueError(f"Unexpected character '{source[pos]}' at position {pos}")

    tokens.append(Token('EOF', '', pos))
    return tokens


def tokens_to_list(tokens: List[Token]) -> List[dict]:
    """Serialize tokens for debugging/reporting."""
    return [{'type': t.token_type, 'value': t.value, 'pos': t.position}
            for t in tokens]
