"""Lexer for the NestedConf (.nconf) configuration format.

Tokenizes raw text into a stream of typed tokens for the parser.
The NestedConf format supports:
  - Sections: [SectionName]
  - Key-value pairs: key = value
  - Quoted strings: key = "value with spaces"
  - Variable references: ${section.key}
  - Comments: # line comment
  - Escape sequences in quoted strings: \\n, \\t, \\\\, \\"
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Token:
    """Represents a single lexical token."""
    type: str
    value: str
    line: int
    column: int


class LexerError(Exception):
    """Raised when the lexer encounters invalid input."""
    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at line {line}, col {column}: {message}")


class NestedConfLexer:
    """Tokenizes NestedConf format text into a token stream.

    Token types produced:
      SECTION_START  - opening bracket [
      SECTION_NAME   - the section identifier
      SECTION_END    - closing bracket ]
      KEY            - a key identifier
      EQUALS         - the = separator
      VALUE          - an unquoted value
      QUOTED_VALUE   - a quoted string (with escapes preserved)
      REFERENCE      - a ${section.key} variable reference
      NEWLINE        - line boundary
      EOF            - end of input
    """

    IDENTIFIER_PATTERN = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
    REFERENCE_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\}')
    WHITESPACE_PATTERN = re.compile(r'[ \t]+')

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Tokenize the entire input text and return the token list."""
        while self.pos < len(self.text):
            # Skip whitespace (not newlines)
            ws_match = self.WHITESPACE_PATTERN.match(self.text, self.pos)
            if ws_match:
                self._advance(len(ws_match.group()))
                continue

            ch = self.text[self.pos]

            # Comments - skip to end of line
            if ch == '#':
                self._skip_comment()
                continue

            # Newlines
            if ch == '\n':
                self.tokens.append(Token('NEWLINE', '\n', self.line, self.column))
                self._advance(1)
                self.line += 1
                self.column = 1
                continue

            # Carriage return (handle \r\n)
            if ch == '\r':
                self._advance(1)
                if self.pos < len(self.text) and self.text[self.pos] == '\n':
                    self._advance(1)
                self.tokens.append(Token('NEWLINE', '\n', self.line, self.column))
                self.line += 1
                self.column = 1
                continue

            # Section header
            if ch == '[':
                self._lex_section_header()
                continue

            # Equals sign
            if ch == '=':
                self.tokens.append(Token('EQUALS', '=', self.line, self.column))
                self._advance(1)
                continue

            # Quoted string
            if ch == '"':
                self._lex_quoted_string()
                continue

            # Variable reference
            if ch == '$' and self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '{':
                self._lex_reference()
                continue

            # Identifier (key name or unquoted value)
            id_match = self.IDENTIFIER_PATTERN.match(self.text, self.pos)
            if id_match:
                self._lex_identifier_or_value(id_match)
                continue

            # Unquoted value (everything else until newline or comment)
            self._lex_unquoted_value()

        self.tokens.append(Token('EOF', '', self.line, self.column))
        return self.tokens

    def _advance(self, count: int):
        """Advance position by count characters."""
        self.pos += count
        self.column += count

    def _skip_comment(self):
        """Skip from # to end of line."""
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance(1)

    def _lex_section_header(self):
        """Lex a section header: [SectionName]."""
        start_line = self.line
        start_col = self.column
        self.tokens.append(Token('SECTION_START', '[', start_line, start_col))
        self._advance(1)

        # Skip whitespace inside brackets
        ws_match = self.WHITESPACE_PATTERN.match(self.text, self.pos)
        if ws_match:
            self._advance(len(ws_match.group()))

        # Read section name
        name_match = self.IDENTIFIER_PATTERN.match(self.text, self.pos)
        if not name_match:
            raise LexerError("Expected section name", self.line, self.column)

        name = name_match.group()
        self.tokens.append(Token('SECTION_NAME', name, self.line, self.column))
        self._advance(len(name))

        # Skip whitespace
        ws_match = self.WHITESPACE_PATTERN.match(self.text, self.pos)
        if ws_match:
            self._advance(len(ws_match.group()))

        # Expect closing bracket
        if self.pos >= len(self.text) or self.text[self.pos] != ']':
            raise LexerError("Expected ']'", self.line, self.column)

        self.tokens.append(Token('SECTION_END', ']', self.line, self.column))
        self._advance(1)

    def _lex_quoted_string(self):
        """Lex a quoted string, preserving escape sequences for later processing."""
        start_line = self.line
        start_col = self.column
        self._advance(1)  # skip opening quote

        result = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                self._advance(1)  # skip closing quote
                self.tokens.append(Token('QUOTED_VALUE', ''.join(result), start_line, start_col))
                return
            elif ch == '\\':
                # Preserve the escape sequence as-is for parser to handle
                result.append('\\')
                self._advance(1)
                if self.pos < len(self.text):
                    result.append(self.text[self.pos])
                    self._advance(1)
            elif ch == '\n':
                raise LexerError("Unterminated string", start_line, start_col)
            else:
                result.append(ch)
                self._advance(1)

        raise LexerError("Unterminated string at EOF", start_line, start_col)

    def _lex_reference(self):
        """Lex a ${section.key} variable reference."""
        start_line = self.line
        start_col = self.column
        ref_match = self.REFERENCE_PATTERN.match(self.text, self.pos)
        if not ref_match:
            raise LexerError("Invalid variable reference", self.line, self.column)

        self.tokens.append(Token('REFERENCE', ref_match.group(1), start_line, start_col))
        self._advance(len(ref_match.group()))

    def _lex_identifier_or_value(self, match):
        """Lex an identifier - determine if it's a key or unquoted value based on context."""
        # Look at previous meaningful token to determine role
        token_type = 'KEY'
        for t in reversed(self.tokens):
            if t.type == 'NEWLINE' or t.type == 'SECTION_END':
                token_type = 'KEY'
                break
            elif t.type == 'EQUALS':
                token_type = 'VALUE'
                break

        value = match.group()
        self.tokens.append(Token(token_type, value, self.line, self.column))
        self._advance(len(value))

    def _lex_unquoted_value(self):
        """Lex an unquoted value - collects until newline or comment."""
        start_line = self.line
        start_col = self.column
        result = []

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch in ('\n', '\r', '#'):
                break
            # Check for inline reference start
            if ch == '$' and self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '{':
                break
            result.append(ch)
            self._advance(1)

        value = ''.join(result).rstrip()  # Trailing whitespace stripped per format spec
        if value:
            self.tokens.append(Token('VALUE', value, start_line, start_col))
