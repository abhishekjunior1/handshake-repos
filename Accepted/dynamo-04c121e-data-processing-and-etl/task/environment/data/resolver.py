"""Resolver for the NestedConf (.nconf) configuration format.

Resolves variable references (${section.key}) by looking up values in
the parsed document tree. Handles circular reference detection and
provides clear error messages for unresolved references.

Resolution strategy:
  1. Build a lookup table from all sections and their key-value pairs
  2. For each value containing references, substitute with resolved values
  3. Detect circular references via visited-set tracking
  4. Unresolvable references are left as literal ${section.key} text

The resolver supports two modes:
  - 'full': Recursively resolves chained references (A->B->C becomes final value)
  - 'shallow': Only resolves direct references (A->B gives B's raw value)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from parser import DocumentNode, SectionNode, ValueNode, ReferenceNode, KeyValueNode


@dataclass
class ResolutionResult:
    """Result of resolving all references in a document."""
    resolved_values: Dict[str, Dict[str, str]] = field(default_factory=dict)
    unresolved_refs: List[str] = field(default_factory=list)
    circular_refs: List[str] = field(default_factory=list)
    resolution_count: int = 0


class ResolutionError(Exception):
    """Raised when reference resolution encounters a fatal error."""
    pass


class NestedConfResolver:
    """Resolves variable references in a parsed NestedConf document.

    Takes a DocumentNode with unresolved ReferenceNodes and produces
    a fully-resolved value mapping. References are resolved using the
    normalized (lowercase) section names for lookup consistency.
    """

    def __init__(self, document: DocumentNode, mode: str = 'full'):
        self.document = document
        self.mode = mode
        self._lookup: Dict[str, Dict[str, ValueNode]] = {}
        self._resolved_cache: Dict[str, str] = {}
        self._resolving: Set[str] = set()

    def resolve(self) -> ResolutionResult:
        """Resolve all references in the document.

        Returns a ResolutionResult containing the fully-resolved values
        organized by section name, plus any unresolved or circular references.
        """
        result = ResolutionResult()

        # Build lookup table using normalized section names
        self._build_lookup_table()

        # Resolve each section's values
        for section in self.document.sections:
            section_values = {}
            for entry in section.entries:
                resolved = self._resolve_value(entry.value, result)
                section_values[entry.key] = resolved
                result.resolution_count += 1

            result.resolved_values[section.name] = section_values

        return result

    def _build_lookup_table(self):
        """Build a lookup table mapping normalized section.key to ValueNodes."""
        for section in self.document.sections:
            if section.name not in self._lookup:
                self._lookup[section.name] = {}
            for entry in section.entries:
                self._lookup[section.name][entry.key] = entry.value

    def _resolve_value(self, value: ValueNode, result: ResolutionResult) -> str:
        """Resolve a single value, substituting any references."""
        parts = []

        for part in value.parts:
            if isinstance(part, ReferenceNode):
                resolved = self._resolve_reference(part, result)
                parts.append(resolved)
            elif isinstance(part, str):
                parts.append(part)
            else:
                parts.append(str(part))

        return ''.join(parts)

    def _resolve_reference(self, ref: ReferenceNode, result: ResolutionResult) -> str:
        """Resolve a single variable reference.

        In 'full' mode, recursively resolves the target value (so chained
        references like A->B->C fully resolve to C's value).
        In 'shallow' mode, returns the target's text representation without
        further resolution (so A->B gives B's raw text including any ${...}).
        """
        # Normalize the reference section name for lookup
        ref_key = f"{ref.section.lower()}.{ref.key}"

        # Check cache first
        if ref_key in self._resolved_cache:
            return self._resolved_cache[ref_key]

        # Detect circular references
        if ref_key in self._resolving:
            result.circular_refs.append(ref_key)
            return f"${{{ref.section}.{ref.key}}}"

        # Look up the referenced value
        section_name = ref.section.lower()
        if section_name not in self._lookup:
            result.unresolved_refs.append(ref_key)
            return f"${{{ref.section}.{ref.key}}}"

        if ref.key not in self._lookup[section_name]:
            result.unresolved_refs.append(ref_key)
            return f"${{{ref.section}.{ref.key}}}"

        # Resolve based on mode
        target_value = self._lookup[section_name][ref.key]

        if self.mode == 'full':
            # Recursively resolve the target value
            self._resolving.add(ref_key)
            resolved = self._resolve_value(target_value, result)
            self._resolving.discard(ref_key)
        else:
            # Shallow: just get the raw text representation
            resolved = target_value.get_resolved_text()

        # Cache the resolved value
        self._resolved_cache[ref_key] = resolved
        return resolved

    def get_section_dependencies(self) -> Dict[str, Set[str]]:
        """Compute dependency graph between sections.

        Returns a mapping from each section to the set of sections it
        references. Useful for determining resolution order.
        """
        dependencies: Dict[str, Set[str]] = {}

        for section in self.document.sections:
            deps = set()
            for entry in section.entries:
                for part in entry.value.parts:
                    if isinstance(part, ReferenceNode):
                        target_section = part.section.lower()
                        if target_section != section.name:
                            deps.add(target_section)
            dependencies[section.name] = deps

        return dependencies

    def get_resolution_order(self) -> List[str]:
        """Determine topological order for section resolution.

        Sections with no dependencies are resolved first, followed by
        sections that depend on already-resolved sections.
        """
        deps = self.get_section_dependencies()
        resolved_sections: List[str] = []
        remaining = set(deps.keys())

        while remaining:
            ready = set()
            for section in remaining:
                if deps[section].issubset(set(resolved_sections)):
                    ready.add(section)

            if not ready:
                ready.add(min(remaining))

            resolved_sections.extend(sorted(ready))
            remaining -= ready

        return resolved_sections
