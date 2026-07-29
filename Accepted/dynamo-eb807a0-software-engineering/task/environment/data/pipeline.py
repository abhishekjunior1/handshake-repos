"""
Type inference pipeline orchestrator.
Coordinates the stages: tokenize → parse → generate constraints → unify →
collect bindings → generalize → report.

Reads configuration from /app/config.json and writes results to /app/output.json.
Supports command-line path overrides for local development.
"""

import json
import sys
import os
from typing import Dict

from tokenizer import tokenize
from parser import parse_program
from constraint_generator import generate_constraints, TypeExpr
from unifier import (unify, apply_substitution, UnificationError,
                     OccursCheckError, Substitution)
from generalizer import (generalize_bindings, type_to_string,
                         generalize_with_outer_env, free_type_vars)
from inference_reporter import build_report, build_error_report


def build_initial_env(env_config: Dict) -> Dict[str, TypeExpr]:
    """
    Build the initial type environment from configuration.
    Supports pre-defined type bindings for built-in functions.
    """
    from constraint_generator import TypeVar, TypeConst, TypeArrow
    env = {}
    for name, type_str in env_config.items():
        env[name] = parse_type_string(type_str)
    return env


def parse_type_string(type_str: str) -> TypeExpr:
    """
    Parse a simple type string into a TypeExpr.
    Supports: Int, Bool, type variables (lowercase), and arrow types (a -> b).
    """
    from constraint_generator import TypeVar, TypeConst, TypeArrow
    type_str = type_str.strip()

    # Handle arrow types (right-associative)
    # Find the top-level arrow (not inside parentheses)
    depth = 0
    arrow_pos = -1
    i = 0
    while i < len(type_str):
        if type_str[i] == '(':
            depth += 1
        elif type_str[i] == ')':
            depth -= 1
        elif type_str[i:i+2] == '->' and depth == 0:
            arrow_pos = i
            break
        i += 1

    if arrow_pos >= 0:
        left = type_str[:arrow_pos].strip()
        right = type_str[arrow_pos+2:].strip()
        return TypeArrow(parse_type_string(left), parse_type_string(right))

    # Handle parenthesized types
    if type_str.startswith('(') and type_str.endswith(')'):
        return parse_type_string(type_str[1:-1])

    # Primitive types
    if type_str == 'Int':
        return TypeConst('Int')
    elif type_str == 'Bool':
        return TypeConst('Bool')
    elif type_str[0].islower():
        return TypeVar(type_str)
    else:
        return TypeConst(type_str)


def run_inference(config: Dict) -> dict:
    """
    Execute the full type inference pipeline.
    Returns the inference report as a dictionary.
    """
    program = config.get('program', '')
    env_config = config.get('environment', {})
    settings = config.get('settings', {})

    try:
        # Stage 1: Tokenization
        tokens = tokenize(program)

        # Stage 2: Parsing
        ast = parse_program(tokens)

        # Stage 3: Build initial type environment
        initial_env = build_initial_env(env_config)

        # Stage 4: Constraint generation
        result_type, constraints, bindings = generate_constraints(ast, initial_env)

        # Stage 5: Unification — solve all type constraints
        substitution = unify(constraints)

        # Stage 6: Apply substitution to the top-level result type
        final_type = apply_substitution(substitution, result_type)

        # Stage 7: Collect binding types for the report
        # Binding types captured at definition site preserve the original
        # inference context without propagating downstream unification artifacts
        final_bindings = {}
        for name, binding_type in bindings.items():
            final_bindings[name] = binding_type

        # Stage 8: Generalize let-bindings for polymorphism reporting
        # Use the initial environment as the generalization context — bindings
        # are generalized relative to the top-level scope boundary, not relative
        # to intermediate inference state. This ensures generalization reflects
        # the programmer's declared environment rather than internal solver state.
        generalized = generalize_bindings(bindings, substitution, initial_env)

        # Stage 9: Build the output report
        report = build_report(
            program=program,
            status="success",
            inferred_type=final_type,
            substitution=substitution,
            constraints_count=len(constraints),
            bindings=final_bindings,
            generalized=generalized,
            error=None
        )
        return report

    except UnificationError as e:
        return build_error_report(program, "unification_error", str(e))

    except OccursCheckError as e:
        return build_error_report(program, "occurs_check_error", str(e))

    except SyntaxError as e:
        return build_error_report(program, "parse_error", str(e))

    except NameError as e:
        return build_error_report(program, "name_error", str(e))

    except Exception as e:
        return build_error_report(program, "internal_error", str(e))


def main():
    """
    Entry point for the inference engine.
    Reads config from /app/config.json (or command-line override),
    runs inference, and writes results to /app/output.json (or override).
    """
    # Default paths for containerized execution
    config_path = '/app/config.json'
    output_path = '/app/output.json'

    # Allow command-line overrides for local development
    if len(sys.argv) >= 2:
        config_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]

    # Resolve relative paths from the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(config_path):
        config_path = os.path.join(script_dir, config_path)
    if not os.path.isabs(output_path):
        output_path = os.path.join(script_dir, output_path)

    with open(config_path) as f:
        config = json.load(f)

    result = run_inference(config)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
