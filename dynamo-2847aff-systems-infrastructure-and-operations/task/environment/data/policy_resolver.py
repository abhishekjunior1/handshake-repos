"""Zone-pair policy resolver for mapping traffic flows to rule sets."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rule_engine import FirewallRule, parse_ruleset


@dataclass
class ZonePairPolicy:
    """Policy binding for a specific source-zone to destination-zone pair."""

    source_zone: str
    dest_zone: str
    ruleset_name: str
    rules: List[FirewallRule] = field(default_factory=list)
    description: str = ""

    def get_key(self) -> Tuple[str, str]:
        """Return the directional key for this zone pair."""
        return (self.source_zone, self.dest_zone)


@dataclass
class PolicyTable:
    """Lookup table mapping zone-pair keys to their associated rule sets."""

    policies: Dict[Tuple[str, str], ZonePairPolicy] = field(default_factory=dict)
    default_action: str = "deny"

    def add_policy(self, policy: ZonePairPolicy) -> None:
        """Register a zone-pair policy in the table."""
        key = policy.get_key()
        self.policies[key] = policy

    def lookup(self, key: Tuple[str, str]) -> Optional[ZonePairPolicy]:
        """Look up policy for a given zone-pair key."""
        return self.policies.get(key)

    def get_rules_for_pair(self, key: Tuple[str, str]) -> Optional[List[FirewallRule]]:
        """Get the rule list for a zone pair, or None if no policy exists."""
        policy = self.policies.get(key)
        if policy is not None:
            return policy.rules
        return None

    def has_policy(self, key: Tuple[str, str]) -> bool:
        """Check if a policy exists for the given zone pair."""
        return key in self.policies

    def list_pairs(self) -> List[Tuple[str, str]]:
        """Return all configured zone-pair keys."""
        return list(self.policies.keys())


def parse_policy_config(config: dict) -> PolicyTable:
    """Parse zone-pair policy configuration into a PolicyTable.

    Expected format:
    {
        "zone_pair_policies": [
            {
                "source_zone": "zone_a",
                "dest_zone": "zone_b",
                "ruleset_name": "a-to-b-rules",
                "description": "...",
                "rules": [...]
            }
        ]
    }
    """
    table = PolicyTable()
    table.default_action = config.get("default_policy_action", "deny")

    for pair_def in config.get("zone_pair_policies", []):
        source_zone = pair_def["source_zone"]
        dest_zone = pair_def["dest_zone"]
        ruleset_name = pair_def.get("ruleset_name", f"{source_zone}-to-{dest_zone}")
        description = pair_def.get("description", "")
        rules = parse_ruleset(pair_def.get("rules", []))

        policy = ZonePairPolicy(
            source_zone=source_zone,
            dest_zone=dest_zone,
            ruleset_name=ruleset_name,
            rules=rules,
            description=description,
        )
        table.add_policy(policy)

    return table


def resolve_policy(
    table: PolicyTable, src_zone: str, dst_zone: str, key_builder
) -> Tuple[Optional[List[FirewallRule]], str]:
    """Resolve the applicable rules for a traffic flow between two zones.

    Uses the provided key_builder function to construct the lookup key.
    Returns (rules_list, ruleset_name) or (None, "") if no policy found.
    """
    key = key_builder(src_zone, dst_zone)
    policy = table.lookup(key)
    if policy is not None:
        return policy.rules, policy.ruleset_name
    return None, ""
