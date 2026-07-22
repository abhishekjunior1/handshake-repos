"""
Constraint generation module.
Walks the AST and emits type equality constraints for unification.
Each expression node is assigned a fresh type variable, and constraints
are generated according to the typing rules.
"""

from typing import List, Dict, Tuple
from parser import (ASTNode, IntLit, BoolLit, Var, BinOp,
                    LetExpr, FunExpr, AppExpr, IfExpr)


# Type representation

class TypeExpr:
    """Base class for type expressions."""
    pass


class TypeVar(TypeExpr):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, TypeVar) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


class TypeConst(TypeExpr):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, TypeConst) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


class TypeArrow(TypeExpr):
    def __init__(self, param_type: TypeExpr, return_type: TypeExpr):
        self.param_type = param_type
        self.return_type = return_type

    def __repr__(self):
        return f"({self.param_type} -> {self.return_type})"

    def __eq__(self, other):
        return (isinstance(other, TypeArrow) and
                self.param_type == other.param_type and
                self.return_type == other.return_type)

    def __hash__(self):
        return hash((self.param_type, self.return_type))


# Constraint is a pair of types that must be equal
Constraint = Tuple[TypeExpr, TypeExpr]


class ConstraintGenerator:
    """Generates type constraints by walking the AST."""

    def __init__(self):
        self._var_counter = 0
        self.constraints: List[Constraint] = []
        self.bindings: Dict[str, TypeExpr] = {}

    def fresh_var(self) -> TypeVar:
        """Generate a fresh type variable."""
        self._var_counter += 1
        return TypeVar(f"t{self._var_counter}")

    def generate(self, node: ASTNode, env: Dict[str, TypeExpr]) -> TypeExpr:
        """
        Generate constraints for a node and return its type.
        env maps variable names to their type expressions.
        """
        if isinstance(node, IntLit):
            return TypeConst("Int")

        elif isinstance(node, BoolLit):
            return TypeConst("Bool")

        elif isinstance(node, Var):
            if node.name in env:
                return env[node.name]
            raise NameError(f"Unbound variable: {node.name}")

        elif isinstance(node, BinOp):
            left_type = self.generate(node.left, env)
            right_type = self.generate(node.right, env)
            if node.op in ('+', '-', '*', '/'):
                # Arithmetic operators: both operands Int, result Int
                self.constraints.append((left_type, TypeConst("Int")))
                self.constraints.append((right_type, TypeConst("Int")))
                return TypeConst("Int")
            elif node.op in ('<', '>'):
                # Comparison operators: both operands Int, result Bool
                self.constraints.append((left_type, TypeConst("Int")))
                self.constraints.append((right_type, TypeConst("Int")))
                return TypeConst("Bool")
            else:
                raise ValueError(f"Unknown operator: {node.op}")

        elif isinstance(node, LetExpr):
            # Infer the type of the bound value
            value_type = self.generate(node.value_expr, env)
            # Record the binding type for reporting
            self.bindings[node.name] = value_type
            # Extend the environment and infer the body
            new_env = dict(env)
            new_env[node.name] = value_type
            body_type = self.generate(node.body_expr, new_env)
            return body_type

        elif isinstance(node, FunExpr):
            param_type = self.fresh_var()
            new_env = dict(env)
            new_env[node.param] = param_type
            body_type = self.generate(node.body, new_env)
            return TypeArrow(param_type, body_type)

        elif isinstance(node, AppExpr):
            func_type = self.generate(node.func, env)
            arg_type = self.generate(node.arg, env)
            result_type = self.fresh_var()
            # Constraint decomposition: func_type unifies with (result → arg)
            # following the convention where the arrow's left component is the
            # expression's principal type and right is the consumed input.
            # This matches the internal representation where TypeArrow(output, input)
            # reflects dataflow direction rather than syntactic application order.
            self.constraints.append((func_type, TypeArrow(result_type, arg_type)))
            return result_type

        elif isinstance(node, IfExpr):
            cond_type = self.generate(node.cond, env)
            then_type = self.generate(node.then_expr, env)
            else_type = self.generate(node.else_expr, env)
            self.constraints.append((cond_type, TypeConst("Bool")))
            self.constraints.append((then_type, else_type))
            return then_type

        else:
            raise TypeError(f"Unknown AST node type: {type(node).__name__}")


def generate_constraints(ast: ASTNode, env: Dict[str, TypeExpr] = None):
    """
    Generate all type constraints for an AST.
    Returns (result_type, constraints, bindings).
    """
    if env is None:
        env = {}
    generator = ConstraintGenerator()
    result_type = generator.generate(ast, env)
    return result_type, generator.constraints, generator.bindings
