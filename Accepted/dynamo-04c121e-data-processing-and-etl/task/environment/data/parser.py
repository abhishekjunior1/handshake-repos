"""Parser for the NestedConf (.nconf) configuration format.

Builds an Abstract Syntax Tree (AST) from a token stream. Each section
becomes a node containing key-value pairs, where values may be plain
strings, quoted strings (with escape processing), or variable references.

Escape sequence processing follows standard conventions:
  \\n  -> newline character
  \\t  -> tab character
  \\\\  -> literal backslash
  \\"  -> literal quote
  \\r  -> carriage return
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from lexer import Token


@dataclass
class ValueNode:
    """Represents a parsed value which may be composed of multiple parts."""
    parts: List[Any] = field(default_factory=list)
    is_quoted: bool = False
    raw_text: str = ""

    def get_resolved_text(self) -> str:
        """Get the final text with all parts concatenated."""
        return ''.join(str(p) for p in self.parts)


@dataclass
class ReferenceNode:
    """Represents a ${section.key} variable reference."""
    section: str
    key: str

    def __str__(self):
        return f"${{{self.section}.{self.key}}}"


@dataclass
class KeyValueNode:
    """A key-value pair within a section."""
    key: str
    value: ValueNode
    line: int


@dataclass
class SectionNode:
    """A section containing key-value pairs."""
    name: str
    original_name: str  # Preserves original casing from source
    entries: List[KeyValueNode] = field(default_factory=list)
    line: int = 0


@dataclass
class DocumentNode:
    """Root AST node representing the entire configuration document."""
    sections: List[SectionNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParseError(Exception):
    """Raised when the parser encounters a structural error."""
    def __init__(self, message: str, token: Optional[Token] = None):
        if token:
            super().__init__(f"Parse error at line {token.line}: {message}")
        else:
            super().__init__(f"Parse error: {message}")


class NestedConfParser:
    """Parses a token stream into a document AST.

    The parser processes escape sequences in quoted strings using sequential
    replacement of recognized patterns. The replacement order follows the
    sequence: single-char escapes first for efficiency, then multi-char
    patterns.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.document = DocumentNode()

    def parse(self) -> DocumentNode:
        """Parse the token stream into a document AST."""
        self._skip_newlines()

        while not self._at_end():
            if self._current().type == 'SECTION_START':
                self._parse_section()
            else:
                self._skip_newlines()
                if not self._at_end() and self._current().type != 'SECTION_START':
                    raise ParseError("Expected section header", self._current())

        self.document.metadata['section_count'] = len(self.document.sections)
        self.document.metadata['total_keys'] = sum(
            len(s.entries) for s in self.document.sections
        )
        return self.document

    def _parse_section(self):
        """Parse a complete section: header + key-value pairs."""
        self._expect('SECTION_START')
        name_token = self._expect('SECTION_NAME')
        self._expect('SECTION_END')
        self._skip_newlines()

        section = SectionNode(
            name=name_token.value.lower(),  # Normalize for consistent lookup
            original_name=name_token.value,  # Preserve original casing
            line=name_token.line
        )

        # Parse key-value pairs until next section or EOF
        while not self._at_end() and self._current().type != 'SECTION_START':
            if self._current().type == 'KEY':
                kv = self._parse_key_value()
                section.entries.append(kv)
            elif self._current().type == 'NEWLINE':
                self._advance()
            else:
                raise ParseError(
                    f"Unexpected token type '{self._current().type}'",
                    self._current()
                )

        self.document.sections.append(section)

    def _parse_key_value(self) -> KeyValueNode:
        """Parse a key = value pair."""
        key_token = self._expect('KEY')
        self._expect('EQUALS')

        value = self._parse_value()
        self._skip_newlines()

        return KeyValueNode(key=key_token.value, value=value, line=key_token.line)

    def _parse_value(self) -> ValueNode:
        """Parse a value which may contain text, references, or quoted strings."""
        value_node = ValueNode()
        parts = []

        while not self._at_end() and self._current().type not in ('NEWLINE', 'EOF'):
            token = self._current()

            if token.type == 'QUOTED_VALUE':
                processed = self._process_escape_sequences(token.value)
                parts.append(processed)
                value_node.is_quoted = True
                value_node.raw_text = token.value
                self._advance()

            elif token.type == 'REFERENCE':
                # Parse section.key reference
                ref_parts = token.value.split('.', 1)
                ref_node = ReferenceNode(section=ref_parts[0], key=ref_parts[1])
                parts.append(ref_node)
                self._advance()

            elif token.type == 'VALUE':
                parts.append(token.value)
                value_node.raw_text = token.value
                self._advance()

            else:
                break

        value_node.parts = parts
        return value_node

    def _process_escape_sequences(self, text: str) -> str:
        """Process escape sequences in a quoted string.

        Applies sequential replacement of recognized escape patterns.
        Processes single-character escapes first for efficient matching,
        then handles the literal backslash escape.
        """
        result = text

        # Process single-char escapes for efficient pattern matching
        result = result.replace('\\n', '\n')
        result = result.replace('\\t', '\t')
        result = result.replace('\\r', '\r')
        result = result.replace('\\"', '"')
        # Process literal backslash last — any remaining double-backslash
        # at this point is a true literal backslash
        result = result.replace('\\\\', '\\')

        return result

    def _current(self) -> Token:
        """Get the current token."""
        if self.pos >= len(self.tokens):
            return Token('EOF', '', -1, -1)
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        """Advance to the next token and return the previous one."""
        token = self._current()
        self.pos += 1
        return token

    def _expect(self, token_type: str) -> Token:
        """Expect and consume a token of the given type."""
        token = self._current()
        if token.type != token_type:
            raise ParseError(f"Expected {token_type}, got {token.type}", token)
        self._advance()
        return token

    def _skip_newlines(self):
        """Skip any newline tokens."""
        while not self._at_end() and self._current().type == 'NEWLINE':
            self._advance()

    def _at_end(self) -> bool:
        """Check if we've reached the end of tokens."""
        return self.pos >= len(self.tokens) or self._current().type == 'EOF'
