"""
Inference result reporter.
Formats the type inference output into the standard JSON structure
for consumption by downstream tooling.
"""

from typing import Dict, Optional
from constraint_generator import TypeExpr
from unifier import Substitution
from generalizer import TypeScheme, type_to_string


def format_substitution(subst: Substitution) -> Dict[str, str]:
    """Convert substitution to serializable string form."""
    result = {}
    for var_name, type_expr in sorted(subst.items()):
        result[var_name] = type_to_string(type_expr)
    return result


def format_bindings(bindings: Dict[str, TypeExpr]) -> Dict[str, str]:
    """Convert binding types to serializable string form."""
    result = {}
    for name, type_expr in bindings.items():
        result[name] = type_to_string(type_expr)
    return result


def format_generalized(schemes: Dict[str, TypeScheme]) -> Dict[str, dict]:
    """Convert type schemes to serializable form."""
    result = {}
    for name, scheme in schemes.items():
        result[name] = scheme.to_dict()
    return result


def build_report(program: str,
                 status: str,
                 inferred_type: Optional[TypeExpr],
                 substitution: Substitution,
                 constraints_count: int,
                 bindings: Dict[str, TypeExpr],
                 generalized: Dict[str, TypeScheme],
                 error: Optional[str] = None) -> dict:
    """
    Build the final inference report dictionary.
    All type expressions are converted to their string representations.
    """
    return {
        "program": program,
        "status": status,
        "inferred_type": type_to_string(inferred_type) if inferred_type else None,
        "substitution": format_substitution(substitution),
        "constraints_generated": constraints_count,
        "bindings": format_bindings(bindings),
        "generalized_types": format_generalized(generalized),
        "error": error
    }


def build_error_report(program: str, status: str, error_message: str) -> dict:
    """Build an error report when inference fails."""
    return {
        "program": program,
        "status": status,
        "inferred_type": None,
        "substitution": {},
        "constraints_generated": 0,
        "bindings": {},
        "generalized_types": {},
        "error": error_message
    }
