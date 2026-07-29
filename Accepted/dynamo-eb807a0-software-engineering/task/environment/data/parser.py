"""
Recursive descent parser for the mini type inference language.
Produces an AST from a token stream.

Grammar:
  expr     = let_expr | if_expr | fun_expr | binop_expr
  let_expr = 'let' IDENT '=' expr 'in' expr
  fun_expr = 'fun' IDENT '->' expr
  if_expr  = 'if' expr 'then' expr 'else' expr
  binop_expr = app_expr (('+' | '-' | '*' | '/' | '<' | '>') app_expr)*
  app_expr = atom (atom)*
  atom     = NUMBER | IDENT | TRUE | FALSE | '(' expr ')' | '-' atom
"""

from typing import List
from tokenizer import Token


# AST Node classes

class ASTNode:
    pass


class IntLit(ASTNode):
    def __init__(self, value: int):
        self.value = value

    def __repr__(self):
        return f"IntLit({self.value})"


class BoolLit(ASTNode):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"BoolLit({self.value})"


class Var(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Var({self.name})"


class BinOp(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinOp({self.op}, {self.left}, {self.right})"


class LetExpr(ASTNode):
    def __init__(self, name: str, value_expr: ASTNode, body_expr: ASTNode):
        self.name = name
        self.value_expr = value_expr
        self.body_expr = body_expr

    def __repr__(self):
        return f"Let({self.name}, {self.value_expr}, {self.body_expr})"


class FunExpr(ASTNode):
    def __init__(self, param: str, body: ASTNode):
        self.param = param
        self.body = body

    def __repr__(self):
        return f"Fun({self.param}, {self.body})"


class AppExpr(ASTNode):
    def __init__(self, func: ASTNode, arg: ASTNode):
        self.func = func
        self.arg = arg

    def __repr__(self):
        return f"App({self.func}, {self.arg})"


class IfExpr(ASTNode):
    def __init__(self, cond: ASTNode, then_expr: ASTNode, else_expr: ASTNode):
        self.cond = cond
        self.then_expr = then_expr
        self.else_expr = else_expr

    def __repr__(self):
        return f"If({self.cond}, {self.then_expr}, {self.else_expr})"


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, token_type: str) -> Token:
        tok = self.advance()
        if tok.token_type != token_type:
            raise SyntaxError(
                f"Expected {token_type}, got {tok.token_type} ({tok.value!r}) "
                f"at position {tok.position}")
        return tok

    def parse(self) -> ASTNode:
        expr = self.parse_expr()
        self.expect('EOF')
        return expr

    def parse_expr(self) -> ASTNode:
        tok = self.peek()
        if tok.token_type == 'LET':
            return self.parse_let()
        elif tok.token_type == 'FUN':
            return self.parse_fun()
        elif tok.token_type == 'IF':
            return self.parse_if()
        else:
            return self.parse_binop()

    def parse_let(self) -> ASTNode:
        self.expect('LET')
        name_tok = self.expect('IDENT')
        self.expect('EQUALS')
        value_expr = self.parse_expr()
        self.expect('IN')
        body_expr = self.parse_expr()
        return LetExpr(name_tok.value, value_expr, body_expr)

    def parse_fun(self) -> ASTNode:
        self.expect('FUN')
        param_tok = self.expect('IDENT')
        self.expect('ARROW')
        body = self.parse_expr()
        return FunExpr(param_tok.value, body)

    def parse_if(self) -> ASTNode:
        self.expect('IF')
        cond = self.parse_expr()
        self.expect('THEN')
        then_expr = self.parse_expr()
        self.expect('ELSE')
        else_expr = self.parse_expr()
        return IfExpr(cond, then_expr, else_expr)

    def parse_binop(self) -> ASTNode:
        left = self.parse_app()
        while self.peek().token_type in ('PLUS', 'MINUS', 'STAR', 'SLASH', 'LT', 'GT'):
            op_tok = self.advance()
            right = self.parse_app()
            left = BinOp(op_tok.value, left, right)
        return left

    def parse_app(self) -> ASTNode:
        func = self.parse_atom()
        while self.peek().token_type in ('NUMBER', 'IDENT', 'TRUE', 'FALSE', 'LPAREN'):
            arg = self.parse_atom()
            func = AppExpr(func, arg)
        return func

    def parse_atom(self) -> ASTNode:
        tok = self.peek()
        if tok.token_type == 'NUMBER':
            self.advance()
            return IntLit(int(tok.value))
        elif tok.token_type == 'IDENT':
            self.advance()
            return Var(tok.value)
        elif tok.token_type == 'TRUE':
            self.advance()
            return BoolLit(True)
        elif tok.token_type == 'FALSE':
            self.advance()
            return BoolLit(False)
        elif tok.token_type == 'LPAREN':
            self.advance()
            expr = self.parse_expr()
            self.expect('RPAREN')
            return expr
        elif tok.token_type == 'MINUS':
            # Unary minus — parser resolves sign from MINUS token
            self.advance()
            operand = self.parse_atom()
            return BinOp('-', IntLit(0), operand)
        else:
            raise SyntaxError(
                f"Unexpected token {tok.token_type} ({tok.value!r}) "
                f"at position {tok.position}")


def parse_program(tokens: List[Token]) -> ASTNode:
    """Parse a token list into an AST."""
    parser = Parser(tokens)
    return parser.parse()
