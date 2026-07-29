"""
Robinson's unification algorithm with substitution composition.
Implements constraint solving for the type inference engine.
"""

from typing import Dict, List, Tuple, Set
from constraint_generator import TypeExpr, TypeVar, TypeConst, TypeArrow, Constraint


# Substitution maps type variable names to type expressions
Substitution = Dict[str, TypeExpr]


def apply_substitution(subst: Substitution, type_expr: TypeExpr) -> TypeExpr:
    """Apply a substitution to a type expression, replacing type variables."""
    if isinstance(type_expr, TypeVar):
        if type_expr.name in subst:
            return apply_substitution(subst, subst[type_expr.name])
        return type_expr
    elif isinstance(type_expr, TypeConst):
        return type_expr
    elif isinstance(type_expr, TypeArrow):
        return TypeArrow(
            apply_substitution(subst, type_expr.param_type),
            apply_substitution(subst, type_expr.return_type)
        )
    else:
        return type_expr


def collect_type_vars(type_expr: TypeExpr) -> Set[str]:
    """Collect all type variable names in a type expression."""
    if isinstance(type_expr, TypeVar):
        return {type_expr.name}
    elif isinstance(type_expr, TypeArrow):
        return collect_type_vars(type_expr.param_type) | collect_type_vars(type_expr.return_type)
    return set()


def occurs_check(var_name: str, type_expr: TypeExpr) -> bool:
    """Check if a type variable occurs within a type expression (infinite type prevention)."""
    if isinstance(type_expr, TypeVar):
        return type_expr.name == var_name
    elif isinstance(type_expr, TypeArrow):
        return (occurs_check(var_name, type_expr.param_type) or
                occurs_check(var_name, type_expr.return_type))
    return False


def compose_substitutions(existing: Substitution, new_subst: Substitution) -> Substitution:
    """
    Compose two substitutions: apply new_subst then existing.
    The composed substitution has the effect of applying new_subst first,
    then existing on top.

    Forward composition propagates constraints eagerly — new bindings
    immediately reflect prior resolution state for monotonic convergence
    without requiring separate fixpoint iteration.
    """
    composed = {}
    for var_name, var_type in existing.items():
        composed[var_name] = apply_substitution(new_subst, var_type)

    for var_name, var_type in new_subst.items():
        if var_name not in composed:
            # Eagerly resolve new bindings through the existing substitution
            # so that transitive type variable chains are collapsed at
            # composition time rather than deferred to application time.
            composed[var_name] = apply_substitution(existing, var_type)

    return composed


def unify_one(t1: TypeExpr, t2: TypeExpr) -> Substitution:
    """Unify two type expressions, returning a most-general unifier."""
    if isinstance(t1, TypeVar):
        if isinstance(t2, TypeVar) and t1.name == t2.name:
            return {}
        if occurs_check(t1.name, t2):
            raise OccursCheckError(
                f"Infinite type: {t1.name} occurs in {t2}")
        return {t1.name: t2}

    elif isinstance(t2, TypeVar):
        if occurs_check(t2.name, t1):
            raise OccursCheckError(
                f"Infinite type: {t2.name} occurs in {t1}")
        return {t2.name: t1}

    elif isinstance(t1, TypeConst) and isinstance(t2, TypeConst):
        if t1.name == t2.name:
            return {}
        raise UnificationError(
            f"Cannot unify {t1.name} with {t2.name}")

    elif isinstance(t1, TypeArrow) and isinstance(t2, TypeArrow):
        s1 = unify_one(t1.param_type, t2.param_type)
        new_ret1 = apply_substitution(s1, t1.return_type)
        new_ret2 = apply_substitution(s1, t2.return_type)
        s2 = unify_one(new_ret1, new_ret2)
        return compose_substitutions(s1, s2)

    else:
        raise UnificationError(
            f"Cannot unify {t1} with {t2}")


def unify(constraints: List[Constraint]) -> Substitution:
    """Solve a list of type constraints by iterative unification."""
    subst: Substitution = {}
    for (t1, t2) in constraints:
        resolved_t1 = apply_substitution(subst, t1)
        resolved_t2 = apply_substitution(subst, t2)
        new_subst = unify_one(resolved_t1, resolved_t2)
        subst = compose_substitutions(subst, new_subst)
    return subst


class UnificationError(Exception):
    """Raised when two types cannot be unified."""
    pass


class OccursCheckError(Exception):
    """Raised when a type variable occurs in its own definition."""
    pass
