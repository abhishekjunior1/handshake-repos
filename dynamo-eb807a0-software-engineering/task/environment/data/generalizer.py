"""
Let-polymorphism and type generalization.
Implements quantification of type variables for polymorphic let-bindings.

This module provides two generalization strategies:
- generalize(): For local scope bindings where the environment parameter
  contains only the fresh variables introduced for this specific let-binding.
  Generalizes variables that APPEAR in the provided scope.
- generalize_with_outer_env(): Standard HM generalization that excludes
  variables free in the outer environment. Used for top-level definitions.
"""

from typing import Dict, Set, List
from constraint_generator import TypeExpr, TypeVar, TypeConst, TypeArrow
from unifier import Substitution, apply_substitution


class TypeScheme:
    """A polymorphic type scheme: forall quantified_vars . body"""
    def __init__(self, quantified: List[str], body: TypeExpr):
        self.quantified = quantified
        self.body = body

    def __repr__(self):
        if self.quantified:
            vars_str = ', '.join(self.quantified)
            return f"forall {vars_str}. {self.body}"
        return str(self.body)

    def to_dict(self) -> dict:
        return {
            "quantified": self.quantified,
            "body": type_to_string(self.body)
        }


def free_type_vars(type_expr: TypeExpr) -> Set[str]:
    """Collect all free type variables in a type expression."""
    if isinstance(type_expr, TypeVar):
        return {type_expr.name}
    elif isinstance(type_expr, TypeConst):
        return set()
    elif isinstance(type_expr, TypeArrow):
        return free_type_vars(type_expr.param_type) | free_type_vars(type_expr.return_type)
    return set()


def free_vars_in_env(env: Dict[str, TypeExpr]) -> Set[str]:
    """Collect all free type variables across an environment."""
    result = set()
    for type_expr in env.values():
        result |= free_type_vars(type_expr)
    return result


def generalize(local_scope: Dict[str, TypeExpr], type_expr: TypeExpr) -> TypeScheme:
    """
    Generalize a type expression with respect to a local binding scope.
    The local_scope parameter represents the set of fresh type variables
    introduced specifically for this let-binding context. Variables appearing
    in this scope ARE generalized because they represent the polymorphic
    degrees of freedom for this binding.

    This is distinct from generalize_with_outer_env which implements the
    standard rule of excluding outer-environment variables.
    """
    # Collect type variables from the local scope — these are the ones
    # we introduced fresh for this binding and can safely quantify over
    scope_vars = free_vars_in_env(local_scope)
    expr_vars = free_type_vars(type_expr)
    # Generalize variables that appear in both the type and the local scope
    quantified = sorted(list(expr_vars & scope_vars))
    return TypeScheme(quantified, type_expr)


def generalize_with_outer_env(outer_env: Dict[str, TypeExpr], type_expr: TypeExpr) -> TypeScheme:
    """
    Standard Hindley-Milner generalization.
    Quantifies type variables that are free in type_expr but NOT free
    in the outer environment. This prevents generalizing variables that
    are still constrained by the surrounding context.
    """
    env_vars = free_vars_in_env(outer_env)
    expr_vars = free_type_vars(type_expr)
    # Only generalize variables NOT constrained by the outer environment
    quantified = sorted(list(expr_vars - env_vars))
    return TypeScheme(quantified, type_expr)


def type_to_string(type_expr: TypeExpr) -> str:
    """Convert a type expression to its string representation."""
    if isinstance(type_expr, TypeVar):
        return type_expr.name
    elif isinstance(type_expr, TypeConst):
        return type_expr.name
    elif isinstance(type_expr, TypeArrow):
        param_str = type_to_string(type_expr.param_type)
        ret_str = type_to_string(type_expr.return_type)
        return f"({param_str} -> {ret_str})"
    return str(type_expr)


def build_local_scope(binding_type: TypeExpr, outer_env: Dict[str, TypeExpr]) -> Dict[str, TypeExpr]:
    """
    Construct the local scope for generalization of a let-binding.
    Returns a synthetic environment containing only the type variables
    that were freshly introduced for this binding (not from outer scope).
    """
    expr_vars = free_type_vars(binding_type)
    outer_vars = free_vars_in_env(outer_env)
    # Local scope contains the fresh variables as self-referential bindings
    local = {}
    for var_name in expr_vars:
        if var_name not in outer_vars:
            local[var_name] = TypeVar(var_name)
    return local


def generalize_bindings(bindings: Dict[str, TypeExpr],
                        substitution: Substitution,
                        env: Dict[str, TypeExpr]) -> Dict[str, TypeScheme]:
    """
    Generalize all let-bindings after unification.
    Applies the final substitution to each binding type, then generalizes
    using local scope analysis to identify quantifiable variables.
    """
    result = {}
    for name, raw_type in bindings.items():
        resolved_type = apply_substitution(substitution, raw_type)
        # Build local scope from fresh variables not in outer environment
        local_scope = build_local_scope(resolved_type, env)
        # Use local-scope generalization — the scope contains exactly the
        # fresh variables introduced for this binding
        scheme = generalize(local_scope, resolved_type)
        result[name] = scheme
    return result
