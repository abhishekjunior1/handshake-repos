#!/usr/bin/env python3
"""
AVA + QC_GATE Simulator — Local adversarial verifier audit.

Tests whether the verifier can be fooled AND checks for qc_gate B5 (underdetermined).
Updated July 2026 based on learnings from dynamo-b56f28d.

Usage:
    cd /path/to/your/repo
    python3 ava_simulator.py

Expected output (task is sound):
    copy_expected:    ❌ ATTACK SUCCEEDED  ← always passes locally, IGNORE
    buggy_output:     ✅ BLOCKED
    swap_evals:       ✅ BLOCKED
    tamper_field:     ✅ BLOCKED
    zero_outputs:     ✅ BLOCKED
    rival_solver:     ✅ BLOCKED   ← NEW: catches qc_gate B5
    fixed_output:     ✅ PASS (legitimate)

    QC_GATE B5:       ✅ OK — rival solver differs on eval data

If ANY of attacks 2-6 succeed → fix your tests before pushing.
If QC_GATE B5 check fails → add rule disclosure to instruction.md.
"""

import json
import os
import sys
import shutil
import tempfile
import subprocess
import copy

# ============================================================================
# CONFIGURE FOR YOUR TASK — edit these 4 sections
# ============================================================================

# 1. Paths
TASK_DIR = "task"
EVAL_CONFIG_1 = "eval_config_1.json"    # filename in environment/data/
EVAL_CONFIG_2 = "eval_config_2.json"
OUTPUT_1      = "output_eval_1.json"    # filename agent writes to /app/
OUTPUT_2      = "output_eval_2.json"
EXPECTED_1    = "expected_output_1.json"  # filename in tests/
EXPECTED_2    = "expected_output_2.json"
PIPELINE      = "pipeline.py"

# 2. Patch strings from solve.py (old → new for each bug fix)
#    Copy these EXACTLY from your solve.py
PATCHES = [
    ("node_filter.py",
     '        effect = taint.get("effect")\n        # Only NoExecute blocks new pod scheduling via the admission filter\n        if effect == "NoExecute":\n            if not _all_pods_tolerate_taint(pods, taint):\n                return False\n',
     '        effect = taint.get("effect")\n        if effect in ("NoSchedule", "NoExecute"):\n            if not _all_pods_tolerate_taint(pods, taint):\n                return False\n'),
    ("pipeline.py",
     "        0.0,\n",
     "        system_overhead,\n"),
    ("affinity_resolver.py",
     "    # Match if ANY label key-value pair is found in the pod's labels.\n    # This provides flexible matching across heterogeneous pod sets.\n    for key, value in match_labels.items():\n        if pod_labels.get(key) == value:\n            return True\n    return False\n",
     "    for key, value in match_labels.items():\n        if pod_labels.get(key) != value:\n            return False\n    return True\n"),
]

# 3. Bug discriminator: leave empty since this task uses exact JSON equality
#    The full equality check + pods_on_untainted threshold in test_outputs.py handles it
DISCRIMINATORS = []

# 4. Rival solver patches (for qc_gate B5/C3 check)
#    Drop Bug1's patch to test: does "NoSchedule only" fix still pass?
#    The eval configs have NoExecute taints — so this rival solver produces
#    different output (uses node-a2/node-b2 with NoExecute taint) → C3 safe
RIVAL_SOLVER_DROPS = [
    # Drop node_filter.py patch = rival solver only checks NoSchedule (not NoExecute)
    # This is the exact mutation qc_gate tests for C3
    ("node_filter.py",
     '        effect = taint.get("effect")\n        # Only NoExecute blocks new pod scheduling via the admission filter\n        if effect == "NoExecute":\n            if not _all_pods_tolerate_taint(pods, taint):\n                return False\n',
     '        effect = taint.get("effect")\n        if effect in ("NoSchedule", "NoExecute"):\n            if not _all_pods_tolerate_taint(pods, taint):\n                return False\n'),
]

# ============================================================================
# END CONFIGURATION
# ============================================================================

DATA_DIR  = os.path.join(TASK_DIR, "environment", "data")
TESTS_DIR = os.path.join(TASK_DIR, "tests")
EVAL1 = os.path.join(DATA_DIR, EVAL_CONFIG_1)
EVAL2 = os.path.join(DATA_DIR, EVAL_CONFIG_2)
EXP1  = os.path.join(TESTS_DIR, EXPECTED_1)
EXP2  = os.path.join(TESTS_DIR, EXPECTED_2)


# ── Helpers ──────────────────────────────────────────────────────────────────

def approx_equal(a, b, rel_tol=1e-3):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if b == 0.0: return a == 0.0
        if abs(b) < 1e-10: return abs(a) < 1e-6
        return abs(a - b) / abs(b) < rel_tol
    return a == b


def run_pipeline(src_dir, config_path, output_path):
    """Run pipeline from src_dir on config_path, write to output_path."""
    pipeline_path = os.path.join(src_dir, PIPELINE)
    config_abs = os.path.abspath(config_path)
    output_abs = os.path.abspath(output_path)
    r = subprocess.run(
        ["python3", pipeline_path, config_abs, output_abs],
        capture_output=True, text=True, cwd=src_dir
    )
    return r.returncode == 0, r.stderr[:300] if r.returncode != 0 else ""


def apply_patches(base, patches_to_apply):
    """Copy DATA_DIR to tmp, apply given patches, return tmp path."""
    tmp = tempfile.mkdtemp(prefix="ava_")
    abs_data = os.path.abspath(DATA_DIR)
    shutil.copytree(abs_data, tmp, dirs_exist_ok=True)
    for fname, old, new in patches_to_apply:
        path = os.path.join(tmp, fname)
        if os.path.exists(path):
            c = open(path).read()
            if old in c:
                open(path, "w").write(c.replace(old, new, 1))
            else:
                print(f"    ⚠️  patch not found in {fname}: {repr(old[:40])}")
        else:
            print(f"    ⚠️  file not found: {fname}")
    return tmp


def load(path):
    with open(path) as f: return json.load(f)


def get_stream(output, model_type):
    """Get first stream matching model_type from stream_results."""
    for s in output.get("stream_results", []):
        if s.get("model_type") == model_type:
            return s
    return None


def check_discriminators(out1, out2, label=""):
    """Check discriminator thresholds. Returns (passed, failures)."""
    if not DISCRIMINATORS:
        return True, []
    failures = []
    outputs = {1: out1, 2: out2}
    for model_type, field, op, threshold, eval_num in DISCRIMINATORS:
        output = outputs[eval_num]
        if not output:
            failures.append(f"eval{eval_num}: output missing")
            continue
        stream = get_stream(output, model_type) if model_type else output
        if not stream:
            failures.append(f"eval{eval_num}: stream {model_type} not found")
            continue
        value = stream.get(field)
        if value is None:
            failures.append(f"eval{eval_num} {model_type}.{field}: field missing")
            continue
        ok = (value > threshold if op == ">" else
              value < threshold if op == "<" else
              approx_equal(value, threshold))
        if not ok:
            failures.append(f"eval{eval_num} {model_type}.{field}={value:.4f} must be {op} {threshold}")
    return len(failures) == 0, failures


def check_stream_ids(out1, out2):
    """Check stream IDs match configs."""
    failures = []
    for output, cfg_path, label in [(out1, EVAL1, "eval1"), (out2, EVAL2, "eval2")]:
        if not output or not os.path.exists(cfg_path): continue
        cfg = load(cfg_path)
        exp_ids = {s["stream_id"] for s in cfg.get("streams", [])}
        got_ids = {s["stream_id"] for s in output.get("stream_results", [])}
        if exp_ids and got_ids != exp_ids:
            failures.append(f"{label}: stream_ids {got_ids} != {exp_ids}")
    return len(failures) == 0, failures


def check_full_equality(out1, out2):
    """Deep approx equality check against expected outputs."""
    failures = []
    for out, exp_path, label in [(out1, EXP1, "eval1"), (out2, EXP2, "eval2")]:
        if not out or not os.path.exists(exp_path): continue
        exp = load(exp_path)
        def walk(a, b, path=""):
            if isinstance(a, dict) and isinstance(b, dict):
                for k in b:
                    walk(a.get(k), b.get(k), f"{path}.{k}")
            elif isinstance(a, list) and isinstance(b, list):
                for i, (x, y) in enumerate(zip(a, b)):
                    walk(x, y, f"{path}[{i}]")
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if not approx_equal(a, b):
                    failures.append(f"{label}{path}: {a:.6f} vs {b:.6f}")
            elif a != b:
                failures.append(f"{label}{path}: {a!r} vs {b!r}")
        walk(out, exp)
    return len(failures) == 0, failures[:3]


def run_attack(name, setup_fn, expect_blocked, extra_checks=None):
    """Run one attack, report result. Returns True if test expectation met."""
    tmp_out1 = tempfile.mktemp(suffix=".json")
    tmp_out2 = tempfile.mktemp(suffix=".json")
    out1, out2 = None, None

    try:
        result = setup_fn(tmp_out1, tmp_out2)
        if result is False:
            print(f"  {name}: ⚠️  SETUP FAILED (pipeline error)")
            return False
        out1 = load(tmp_out1) if os.path.exists(tmp_out1) else None
        out2 = load(tmp_out2) if os.path.exists(tmp_out2) else None
    except Exception as e:
        print(f"  {name}: ⚠️  ERROR: {e}")
        return False

    # Run all checks
    all_failures = []

    disc_ok, disc_fails = check_discriminators(out1, out2)
    all_failures.extend(disc_fails)

    ids_ok, ids_fails = check_stream_ids(out1, out2)
    all_failures.extend(ids_fails)

    eq_ok, eq_fails = check_full_equality(out1, out2)
    all_failures.extend(eq_fails)

    attack_passed = len(all_failures) == 0

    if expect_blocked:
        if not attack_passed:
            print(f"  {name}: ✅ BLOCKED ({len(all_failures)} check(s) failed)")
            for f in all_failures[:2]:
                print(f"    blocked by: {f}")
        else:
            print(f"  {name}: ❌ ATTACK SUCCEEDED — verifier accepts wrong output!")
            print(f"    → Fix your input-derivation tests or full-equality tests")
    else:
        if attack_passed:
            print(f"  {name}: ✅ PASS (legitimate output accepted)")
        else:
            print(f"  {name}: ❌ UNEXPECTED FAIL")
            for f in all_failures[:2]:
                print(f"    failing check: {f}")

    for f in [tmp_out1, tmp_out2]:
        if os.path.exists(f): os.remove(f)

    return attack_passed == (not expect_blocked)


# ── Attack definitions ────────────────────────────────────────────────────────

def attack_copy_expected(out1, out2):
    if os.path.exists(EXP1): shutil.copy(EXP1, out1)
    if os.path.exists(EXP2): shutil.copy(EXP2, out2)

def attack_buggy(out1, out2):
    abs_data = os.path.abspath(DATA_DIR)
    ok1, err1 = run_pipeline(abs_data, os.path.abspath(EVAL1), out1)
    ok2, err2 = run_pipeline(abs_data, os.path.abspath(EVAL2), out2)
    if not ok1: print(f"    pipeline error: {err1[:100]}")
    if not ok2: print(f"    pipeline error: {err2[:100]}")

def attack_swap(out1, out2):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1:
        tmp1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2:
        tmp2 = f2.name
    run_pipeline(os.path.abspath(DATA_DIR), os.path.abspath(EVAL1), tmp1)
    run_pipeline(os.path.abspath(DATA_DIR), os.path.abspath(EVAL2), tmp2)
    if os.path.exists(tmp1) and os.path.exists(tmp2):
        shutil.copy(tmp2, out1)  # swap
        shutil.copy(tmp1, out2)
    if os.path.exists(tmp1): os.remove(tmp1)
    if os.path.exists(tmp2): os.remove(tmp2)

def attack_tamper_field(out1, out2):
    """Tamper the discriminator field with buggy values."""
    if not os.path.exists(EXP1) or not os.path.exists(EXP2): return
    d1 = load(EXP1); d2 = load(EXP2)
    # Set discriminator fields to buggy-pipeline values (just below threshold)
    for disc in DISCRIMINATORS:
        model_type, field, op, threshold, eval_num = disc
        data = d1 if eval_num == 1 else d2
        for s in data.get("stream_results", []):
            if model_type and s.get("model_type") == model_type:
                # Set to a value that fails the threshold
                if op == ">":
                    s[field] = threshold * 2 - 1  # below threshold
                else:
                    s[field] = threshold + abs(threshold) * 0.5  # above threshold
    with open(out1, "w") as f: json.dump(d1, f)
    with open(out2, "w") as f: json.dump(d2, f)

def attack_zero_outputs(out1, out2):
    """Zero all numeric values in expected output."""
    if not os.path.exists(EXP1) or not os.path.exists(EXP2): return
    def zero_nums(d):
        if isinstance(d, dict): return {k: zero_nums(v) for k, v in d.items()}
        if isinstance(d, list): return [zero_nums(x) for x in d]
        if isinstance(d, float): return 0.0
        return d
    with open(out1, "w") as f: json.dump(zero_nums(load(EXP1)), f)
    with open(out2, "w") as f: json.dump(zero_nums(load(EXP2)), f)


# ── qc_gate B5 check ──────────────────────────────────────────────────────────

def check_qc_gate_b5():
    """
    Check for qc_gate B5 (Underdetermined/Rival-Solver ambiguity).
    
    A rival solver applies ALL patches EXCEPT the ones in RIVAL_SOLVER_DROPS.
    If the rival solver's output on EVAL datasets is IDENTICAL to oracle → B5 risk.
    """
    print("\n── QC_GATE B5 CHECK ──────────────────────────────────────────")
    print("Testing: does keeping one bug still produce correct output on eval data?")

    if not RIVAL_SOLVER_DROPS:
        print("  SKIP — RIVAL_SOLVER_DROPS is empty (configure it to enable B5 check)")
        return True

    if not PATCHES:
        print("  SKIP — PATCHES is empty")
        return True

    # Build rival patches: all except the dropped ones
    rival_patches = [p for p in PATCHES if p not in RIVAL_SOLVER_DROPS]
    oracle_patches = PATCHES

    if len(rival_patches) == len(oracle_patches):
        print("  SKIP — RIVAL_SOLVER_DROPS doesn't match any PATCHES entries")
        return True

    print(f"  Rival solver: applies {len(rival_patches)}/{len(oracle_patches)} patches")
    print(f"  (Drops: {[p[0] for p in RIVAL_SOLVER_DROPS]})")

    # Run rival solver on visible dataset (should match oracle — this is expected/OK)
    rival_dir = apply_patches(".", rival_patches)
    oracle_dir = apply_patches(".", oracle_patches)

    try:
        # Check visible dataset
        vis_path = os.path.join(DATA_DIR, "dataset.json")
        if os.path.exists(vis_path):
            r_vis = tempfile.mktemp(suffix=".json")
            o_vis = tempfile.mktemp(suffix=".json")
            run_pipeline(rival_dir, vis_path, r_vis)
            run_pipeline(oracle_dir, vis_path, o_vis)
            if os.path.exists(r_vis) and os.path.exists(o_vis):
                r_data = load(r_vis); o_data = load(o_vis)
                vis_same = r_data == o_data
                print(f"  Visible dataset.json: rival {'==' if vis_same else '!='} oracle "
                      f"({'OK — masked' if vis_same else 'DIFFER — masking may be broken'})")
                os.remove(r_vis); os.remove(o_vis)

        # Check eval datasets — this is the critical check
        b5_ok = True
        for cfg, label in [(EVAL1, "eval1"), (EVAL2, "eval2")]:
            r_out = tempfile.mktemp(suffix=".json")
            o_out = tempfile.mktemp(suffix=".json")
            run_pipeline(rival_dir, cfg, r_out)
            run_pipeline(oracle_dir, cfg, o_out)
            if os.path.exists(r_out) and os.path.exists(o_out):
                r_data = load(r_out); o_data = load(o_out)
                same = r_data == o_data
                if same:
                    b5_ok = False
                    print(f"  {label}: rival == oracle ❌ → qc_gate B5 RISK!")
                    print(f"    Fix: add rule disclosure to instruction.md")
                    print(f"    e.g., 'The X is computed as [correct rule], not [rival rule]'")
                else:
                    print(f"  {label}: rival != oracle ✅ ({label} discriminates the dropped bug)")
                os.remove(r_out); os.remove(o_out)
        return b5_ok
    finally:
        shutil.rmtree(rival_dir, ignore_errors=True)
        shutil.rmtree(oracle_dir, ignore_errors=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AVA + QC_GATE SIMULATOR")
    print(f"Task: {os.path.abspath(TASK_DIR)}")
    if DISCRIMINATORS:
        for d in DISCRIMINATORS:
            print(f"  Discriminator eval{d[4]}: {d[1]} {d[2]} {d[3]}")
    print("=" * 60)
    print()

    if not os.path.exists(DATA_DIR):
        print(f"ERROR: DATA_DIR not found: {DATA_DIR}")
        sys.exit(1)

    results = {}

    # ── Attack 1: Copy expected (always passes locally — ignore) ──
    print("Attack 1 — Copy expected fixtures directly:")
    print("  (always passes locally — Harbor prevents this on CI, IGNORE)")
    attack_copy_expected("/tmp/ava_c1.json", "/tmp/ava_c2.json")
    c1 = load("/tmp/ava_c1.json") if os.path.exists("/tmp/ava_c1.json") else None
    c2 = load("/tmp/ava_c2.json") if os.path.exists("/tmp/ava_c2.json") else None
    disc_ok, _ = check_discriminators(c1, c2)
    eq_ok, _ = check_full_equality(c1, c2)
    print(f"  copy_expected: {'❌ ATTACK SUCCEEDED  ← IGNORE (impossible on CI)' if (disc_ok and eq_ok) else '✅ BLOCKED (unusual)'}")
    print()

    # ── Attack 2: Buggy pipeline ──
    print("Attack 2 — Run buggy pipeline (no fix):")
    results["buggy_output"] = run_attack("buggy_output", attack_buggy, expect_blocked=True)
    print()

    # ── Attack 3: Swap evals ──
    print("Attack 3 — Swap eval outputs:")
    results["swap_evals"] = run_attack("swap_evals", attack_swap, expect_blocked=True)
    print()

    # ── Attack 4: Tamper discriminator field ──
    if DISCRIMINATORS:
        print("Attack 4 — Tamper discriminator field to buggy values:")
        results["tamper_field"] = run_attack("tamper_field", attack_tamper_field, expect_blocked=True)
        print()

    # ── Attack 5: Zero all outputs ──
    print("Attack 5 — Zero all numeric outputs:")
    results["zero_outputs"] = run_attack("zero_outputs", attack_zero_outputs, expect_blocked=True)
    print()

    # ── Attack 6: Rival solver (qc_gate B5) ──
    if RIVAL_SOLVER_DROPS and PATCHES:
        rival_patches = [p for p in PATCHES if p not in RIVAL_SOLVER_DROPS]

        def attack_rival(out1, out2):
            rival_dir = apply_patches(".", rival_patches)
            try:
                run_pipeline(rival_dir, EVAL1, out1)
                run_pipeline(rival_dir, EVAL2, out2)
            finally:
                shutil.rmtree(rival_dir, ignore_errors=True)

        print("Attack 6 — Rival solver (keeps one bug, fixes others):")
        print(f"  Tests if dropping {[p[0] for p in RIVAL_SOLVER_DROPS]} is detectable")
        results["rival_solver"] = run_attack("rival_solver", attack_rival, expect_blocked=True)
        print()

    # ── Legitimate: Fixed pipeline ──
    if PATCHES:
        oracle_dir = apply_patches(".", PATCHES)
        def attack_oracle(out1, out2):
            run_pipeline(oracle_dir, EVAL1, out1)
            run_pipeline(oracle_dir, EVAL2, out2)
        print("Legitimate — Fixed pipeline (should pass):")
        results["fixed_output"] = run_attack("fixed_output", attack_oracle, expect_blocked=False)
        shutil.rmtree(oracle_dir, ignore_errors=True)
        print()

    # ── qc_gate B5 detailed check ──
    b5_ok = check_qc_gate_b5()

    # ── Summary ──
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  copy_expected:  ❌ ATTACK SUCCEEDED  ← always local, IGNORE")
    for name, ok in results.items():
        icon = "✅ BLOCKED" if (ok and name != "fixed_output") else ("✅ PASS" if (ok and name == "fixed_output") else "❌ FAILED")
        print(f"  {name}: {icon}")
    print()
    if b5_ok:
        print("  QC_GATE B5:     ✅ OK — rival solver differs on eval data")
    else:
        print("  QC_GATE B5:     ❌ RISK — rival solver identical to oracle on eval data")
        print("                   → Add rule disclosure to instruction.md")
    print()

    all_material_blocked = all(v for k, v in results.items() if k != "fixed_output")
    fixed_passes = results.get("fixed_output", True)

    if all_material_blocked and fixed_passes and b5_ok:
        print("✅ All checks passed — safe to push, AVA and qc_gate should pass.")
        sys.exit(0)
    else:
        print("⚠️  Some checks failed — fix before pushing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
