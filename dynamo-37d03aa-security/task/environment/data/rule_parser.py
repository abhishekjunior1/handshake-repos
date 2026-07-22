"""Rule parser for CIS compliance benchmark definitions.

Parses hierarchical rule structures and builds evaluation trees.
Handles profile → section → control relationships with parent-child
linkage for inheritance resolution.
"""

from typing import Any


class RuleNode:
    """Represents a node in the benchmark hierarchy tree."""

    def __init__(self, node_id: str, node_type: str, data: dict[str, Any],
                 parent: "RuleNode | None" = None):
        self.node_id = node_id
        self.node_type = node_type
        self.data = data
        self.parent = parent
        self.children: list["RuleNode"] = []

    def add_child(self, child: "RuleNode") -> None:
        """Add a child node and set its parent reference."""
        child.parent = self
        self.children.append(child)

    def get_ancestors(self) -> list["RuleNode"]:
        """Walk up the tree to collect all ancestor nodes."""
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_depth(self) -> int:
        """Return the depth of this node in the tree."""
        depth = 0
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def is_leaf(self) -> bool:
        """Check if this node is a leaf (no children)."""
        return len(self.children) == 0

    def get_full_path(self) -> str:
        """Return the full hierarchical path of this node."""
        parts = [self.node_id]
        current = self.parent
        while current is not None:
            parts.append(current.node_id)
            current = current.parent
        return "/".join(reversed(parts))


def parse_benchmark(benchmark: dict[str, Any]) -> dict[str, RuleNode]:
    """Parse benchmark definition into a tree of RuleNodes.

    Returns a dictionary mapping node_id to RuleNode for all nodes
    in the hierarchy (profiles, sections, subsections, controls).
    """
    node_registry: dict[str, RuleNode] = {}

    for profile_data in benchmark.get("profiles", []):
        profile_node = RuleNode(
            node_id=profile_data["id"],
            node_type="profile",
            data=_extract_profile_metadata(profile_data),
        )
        node_registry[profile_node.node_id] = profile_node

        for section_data in profile_data.get("sections", []):
            _parse_section(section_data, profile_node, node_registry)

    return node_registry


def _parse_section(section_data: dict[str, Any], parent: RuleNode,
                   registry: dict[str, RuleNode]) -> None:
    """Recursively parse a section and its children."""
    section_node = RuleNode(
        node_id=section_data["id"],
        node_type="section",
        data=_extract_section_metadata(section_data),
    )
    parent.add_child(section_node)
    registry[section_node.node_id] = section_node

    # Parse subsections recursively
    for subsection_data in section_data.get("subsections", []):
        _parse_section(subsection_data, section_node, registry)

    # Parse controls at this level
    for control_data in section_data.get("controls", []):
        control_node = RuleNode(
            node_id=control_data["id"],
            node_type="control",
            data=control_data,
        )
        section_node.add_child(control_node)
        registry[control_node.node_id] = control_node


def _extract_profile_metadata(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Extract profile-level metadata without nested sections."""
    return {
        "id": profile_data["id"],
        "title": profile_data.get("title", ""),
        "level": profile_data.get("level", 1),
        "description": profile_data.get("description", ""),
        "applicability": profile_data.get("applicability", {}),
    }


def _extract_section_metadata(section_data: dict[str, Any]) -> dict[str, Any]:
    """Extract section-level metadata without nested children."""
    return {
        "id": section_data["id"],
        "title": section_data.get("title", ""),
        "description": section_data.get("description", ""),
        "weight": section_data.get("weight", 1.0),
    }


def get_controls_for_profile(node_registry: dict[str, RuleNode],
                             profile_id: str) -> list[RuleNode]:
    """Get all control nodes belonging to a specific profile."""
    if profile_id not in node_registry:
        return []

    profile_node = node_registry[profile_id]
    controls = []
    _collect_controls(profile_node, controls)
    return controls


def _collect_controls(node: RuleNode, controls: list[RuleNode]) -> None:
    """Recursively collect all control nodes under a given node."""
    if node.node_type == "control":
        controls.append(node)
    for child in node.children:
        _collect_controls(child, controls)


def get_section_controls(node_registry: dict[str, RuleNode],
                         section_id: str) -> list[RuleNode]:
    """Get all controls directly or indirectly under a section."""
    if section_id not in node_registry:
        return []

    section_node = node_registry[section_id]
    controls = []
    _collect_controls(section_node, controls)
    return controls


def get_effective_controls(node_registry: dict[str, RuleNode],
                           profile_id: str,
                           walk_ancestors: bool = True) -> list[dict[str, Any]]:
    """Get effective control set for a profile with inheritance.

    When walk_ancestors is True, controls inherit properties from ancestor
    sections (severity overrides, applicability constraints). When False,
    only the leaf control definition is used without ancestor context.
    """
    controls = get_controls_for_profile(node_registry, profile_id)
    effective = []

    for control in controls:
        control_def = dict(control.data)

        if walk_ancestors:
            # Walk ancestor chain to inherit properties
            ancestors = control.get_ancestors()
            for ancestor in ancestors:
                if ancestor.node_type == "section":
                    # Sections can override severity thresholds
                    if "severity_override" in ancestor.data:
                        control_def["effective_severity"] = ancestor.data["severity_override"]
                    # Sections can define applicability constraints
                    if "applicability" in ancestor.data:
                        if "applicability_constraints" not in control_def:
                            control_def["applicability_constraints"] = []
                        control_def["applicability_constraints"].append(
                            ancestor.data["applicability"]
                        )
                elif ancestor.node_type == "profile":
                    # Profile-level applicability
                    if "applicability" in ancestor.data:
                        if "applicability_constraints" not in control_def:
                            control_def["applicability_constraints"] = []
                        control_def["applicability_constraints"].append(
                            ancestor.data["applicability"]
                        )

        control_def["full_path"] = control.get_full_path()
        control_def["depth"] = control.get_depth()
        effective.append(control_def)

    return effective
