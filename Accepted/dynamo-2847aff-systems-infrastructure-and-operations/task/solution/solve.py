"""Solution: patches pipeline.py to fix NAT ordering, state lookup, and zone-pair key construction."""

import subprocess
import sys


def patch_pipeline():
    """Apply minimal patches to fix the three processing errors in pipeline.py."""
    with open("/app/pipeline.py", "r") as f:
        source = f.read()

    # Fix 1: Change zone-pair key from sorted to directional
    source = source.replace(
        "return tuple(sorted([src_zone, dst_zone]))",
        "return (src_zone, dst_zone)",
    )

    # Fix 2 and 3: Restructure packet processing to apply DNAT before policy
    # evaluation and use translated tuple for state lookup
    old_block = """\
        original_tuple = (src_ip, dst_ip, src_port, dst_port, protocol)

        state_key = original_tuple
        conn_state, existing_flow = flow_table.get_state_for_packet(state_key, timestamp)

        if conn_state == "established" and existing_flow is not None:
            stateful_match_count += 1
            action = existing_flow.action
            matched_rule = existing_flow.rule_name
            nat_applied = False
        else:
            # zone-based first-match semantics
            rules, _ = resolve_policy(
                policy_table, src_zone, dst_zone, build_zone_pair_key
            )

            if rules is None:
                action = "deny"
                matched_rule = "no-policy"
                nat_applied = False
            else:
                rule_result = evaluate_rules(
                    rules, src_ip, dst_ip, src_port, dst_port, protocol
                )
                action = rule_result.action
                matched_rule = rule_result.rule_name

                translated = nat_translator.apply_dnat(
                    src_ip, dst_ip, src_port, dst_port, protocol
                )
                nat_applied = translated[5]
                if nat_applied:
                    nat_translation_count += 1

            flow_table.create_flow(original_tuple, action, timestamp, matched_rule)"""

    new_block = """\
        translated = nat_translator.apply_dnat(
            src_ip, dst_ip, src_port, dst_port, protocol
        )
        t_src_ip, t_dst_ip, t_src_port, t_dst_port, t_protocol, nat_applied = translated

        if nat_applied:
            nat_translation_count += 1

        translated_tuple = (t_src_ip, t_dst_ip, t_src_port, t_dst_port, t_protocol)
        conn_state, existing_flow = flow_table.get_state_for_packet(translated_tuple, timestamp)

        if conn_state == "established" and existing_flow is not None:
            stateful_match_count += 1
            action = existing_flow.action
            matched_rule = existing_flow.rule_name
        else:
            # zone-based first-match semantics
            rules, _ = resolve_policy(
                policy_table, src_zone, dst_zone, build_zone_pair_key
            )

            if rules is None:
                action = "deny"
                matched_rule = "no-policy"
            else:
                rule_result = evaluate_rules(
                    rules, t_src_ip, t_dst_ip, t_src_port, t_dst_port, t_protocol
                )
                action = rule_result.action
                matched_rule = rule_result.rule_name

            flow_table.create_flow(translated_tuple, action, timestamp, matched_rule)"""

    source = source.replace(old_block, new_block)

    with open("/app/pipeline.py", "w") as f:
        f.write(source)


def main():
    """Patch pipeline and run it to produce correct output."""
    patch_pipeline()
    result = subprocess.run(
        ["python3", "/app/pipeline.py"],
        cwd="/app",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
