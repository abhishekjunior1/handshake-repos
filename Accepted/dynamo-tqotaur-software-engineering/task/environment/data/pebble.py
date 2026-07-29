#!/usr/bin/env python3
"""Pebble interpreter."""
import sys, re

KEYWORDS = {'let','mut','fn','if','else','while','for','in','print','true','false','return'}
TOKEN_RE = re.compile(r'(\s+)|(//[^\n]*)|(\d+)|("(?:[^"\\]|\\.)*")|(&?fn)\b|([a-zA-Z_]\w*)|(==|!=|<=|>=|&&|\|\||\.\.)|(.)', re.DOTALL)

def tokenize(src):
    tokens = []
    for m in TOKEN_RE.finditer(src):
        ws, cmt, num, s, fn, ident, op2, ch = m.groups()
        if ws or cmt: continue
        if num: tokens.append(('NUM', int(num)))
        elif s: tokens.append(('STR', s[1:-1].replace('\\n','\n').replace('\\t','\t').replace('\\"','"').replace('\\\\','\\')))
        elif fn: tokens.append(('FN', fn))
        elif ident:
            if ident in ('true','false'): tokens.append(('BOOL', ident=='true'))
            elif ident in KEYWORDS: tokens.append((ident.upper(), ident))
            else: tokens.append(('IDENT', ident))
        elif op2: tokens.append((op2, op2))
        elif ch: tokens.append((ch, ch))
    tokens.append(('EOF', None))
    return tokens

class Parser:
    def __init__(self, tokens): self.t = tokens; self.p = 0
    def peek(self): return self.t[self.p]
    def eat(self, typ=None):
        t = self.t[self.p]; self.p += 1
        if typ and t[0] != typ: raise SyntaxError(f"expected {typ}, got {t}")
        return t
    def program(self):
        s = []
        while self.peek()[0] != 'EOF': s.append(self.stmt())
        return ('block', s)
    def block(self):
        self.eat('{'); s = []
        while self.peek()[1] != '}': s.append(self.stmt())
        self.eat('}'); return ('block', s)
    def stmt(self):
        t = self.peek()
        if t[0] == 'LET': self.eat(); n = self.eat('IDENT')[1]; self.eat('='); v = self.expr(); self.eat(';'); return ('let',n,v)
        elif t[0] == 'MUT': self.eat(); n = self.eat('IDENT')[1]; self.eat('='); v = self.expr(); self.eat(';'); return ('mut',n,v)
        elif t[0] == 'IF': return self.if_s()
        elif t[0] == 'WHILE': self.eat(); c = self.expr(); b = self.block(); return ('while',c,b)
        elif t[0] == 'FOR': self.eat(); n = self.eat('IDENT')[1]; self.eat('IN'); s = self.expr(); self.eat('..'); e = self.expr(); b = self.block(); return ('for',n,s,e,b)
        elif t[0] == 'PRINT': self.eat(); v = self.expr(); self.eat(';'); return ('print',v)
        elif t[0] == 'RETURN': self.eat(); v = self.expr(); self.eat(';'); return ('return',v)
        elif t[0] == 'IDENT':
            n = self.eat()[1]
            if self.peek()[1] == '=': self.eat('='); v = self.expr(); self.eat(';'); return ('assign',n,v)
            self.p -= 1; e = self.expr(); self.eat(';'); return ('expr',e)
        else: e = self.expr(); self.eat(';'); return ('expr',e)
    def if_s(self):
        self.eat(); c = self.expr(); th = self.block(); el = None
        if self.peek()[0] == 'ELSE':
            self.eat()
            el = self.if_s() if self.peek()[0] == 'IF' else self.block()
        return ('if',c,th,el)
    def expr(self): return self.or_e()
    def or_e(self):
        l = self.and_e()
        while self.peek()[1] == '||': self.eat(); l = ('binop','||',l,self.and_e())
        return l
    def and_e(self):
        l = self.eq_e()
        while self.peek()[1] == '&&': self.eat(); l = ('binop','&&',l,self.eq_e())
        return l
    def eq_e(self):
        l = self.cmp_e()
        while self.peek()[1] in ('==','!='): o = self.eat()[1]; l = ('binop',o,l,self.cmp_e())
        return l
    def cmp_e(self):
        l = self.add_e()
        while self.peek()[1] in ('<','>','<=','>='): o = self.eat()[1]; l = ('binop',o,l,self.add_e())
        return l
    def add_e(self):
        l = self.mul_e()
        while self.peek()[1] in ('+','-'): o = self.eat()[1]; l = ('binop',o,l,self.mul_e())
        return l
    def mul_e(self):
        l = self.unary()
        while self.peek()[1] in ('*','/','%'): o = self.eat()[1]; l = ('binop',o,l,self.unary())
        return l
    def unary(self):
        if self.peek()[1] == '-': self.eat(); return ('unary','-',self.unary())
        if self.peek()[1] == '!': self.eat(); return ('unary','!',self.unary())
        return self.call_e()
    def call_e(self):
        e = self.primary()
        while self.peek()[1] == '(':
            self.eat('('); a = []
            if self.peek()[1] != ')':
                a.append(self.expr())
                while self.peek()[1] == ',': self.eat(','); a.append(self.expr())
            self.eat(')'); e = ('call',e,a)
        return e
    def primary(self):
        t = self.peek()
        if t[0] == 'NUM': self.eat(); return ('lit',t[1])
        elif t[0] == 'STR': self.eat(); return ('lit',t[1])
        elif t[0] == 'BOOL': self.eat(); return ('lit',t[1])
        elif t[0] == 'IDENT': self.eat(); return ('var',t[1])
        elif t[0] == 'FN': return self.fn_e()
        elif t[1] == '(': self.eat('('); e = self.expr(); self.eat(')'); return e
        else: raise SyntaxError(f"unexpected {t}")
    def fn_e(self):
        ft = self.eat(); br = ft[1] == '&fn'
        self.eat('('); p = []
        if self.peek()[1] != ')':
            p.append(self.eat('IDENT')[1])
            while self.peek()[1] == ',': self.eat(','); p.append(self.eat('IDENT')[1])
        self.eat(')'); b = self.block()
        return ('fn',p,b,br)

class Cell:
    __slots__ = ['v']
    def __init__(self, v): self.v = v

class Env:
    def __init__(self, parent=None): self.b = {}; self.parent = parent
    def define(self, n, c): self.b[n] = c
    def lookup(self, n):
        if n in self.b: return self.b[n]
        if self.parent: return self.parent.lookup(n)
        raise NameError(n)

class Closure:
    def __init__(self, p, body, env, br): self.p = p; self.body = body; self.env = env; self.br = br

class ReturnExc(Exception):
    def __init__(self, v): self.v = v

class Interp:
    def __init__(self): self.out = []
    def run(self, ast): self.xblock(ast, Env())
    def xblock(self, n, env):
        for s in n[1]: self.xstmt(s, env)
    def xstmt(self, s, env):
        t = s[0]
        if t == 'let': env.define(s[1], Cell(self.xexpr(s[2], env)))
        elif t == 'mut': env.define(s[1], Cell(self.xexpr(s[2], env)))
        elif t == 'assign': env.lookup(s[1]).v = self.xexpr(s[2], env)
        elif t == 'print':
            v = self.xexpr(s[1], env)
            self.out.append(str(v))
        elif t == 'if':
            if self.xexpr(s[1], env): self.xblock(s[2], Env(env))
            elif s[3]:
                if s[3][0] == 'if': self.xstmt(s[3], env)
                else: self.xblock(s[3], Env(env))
        elif t == 'while':
            while self.xexpr(s[1], env): self.xblock(s[2], Env(env))
        elif t == 'for':
            st = self.xexpr(s[2], env); en = self.xexpr(s[3], env)
            ie = Env(env); ie.define(s[1], Cell(st))
            for i in range(st, en):
                ie.lookup(s[1]).val = i; self.xblock(s[4], ie)
        elif t == 'return': raise ReturnExc(self.xexpr(s[1], env))
        elif t == 'expr': self.xexpr(s[1], env)
    def xexpr(self, e, env):
        t = e[0]
        if t == 'lit': return e[1]
        elif t == 'var': return env.lookup(e[1]).v
        elif t == 'unary':
            v = self.xexpr(e[2], env)
            return -v if e[1] == '-' else not v
        elif t == 'binop':
            op = e[1]
            if op == '&&': return self.xexpr(e[2], env) and self.xexpr(e[3], env)
            if op == '||': return self.xexpr(e[2], env) or self.xexpr(e[3], env)
            l = self.xexpr(e[2], env); r = self.xexpr(e[3], env)
            if op == '+': return (str(l)+str(r)) if isinstance(l,str) or isinstance(r,str) else l+r
            if op == '-': return l-r
            if op == '*': return l*r
            if op == '/': return l//r
            if op == '%': return l%r
            if op == '<': return l<r
            if op == '>': return l>r
            if op == '<=': return l<=r
            if op == '>=': return l>=r
            if op == '==': return l==r
            if op == '!=': return l!=r
        elif t == 'fn':
            params, body, by_ref = e[1], e[2], e[3]
            if by_ref:
                return Closure(params, body, env, True)
            else:
                # Capture immediate scope only — Pebble's fn semantics
                captured = Env(env.parent)
                for name, cell in env.b.items():
                    captured.b[name] = Cell(cell.v)
                return Closure(params, body, captured, False)
        elif t == 'call':
            fn = self.xexpr(e[1], env)
            args = [self.xexpr(a, env) for a in e[2]]
            return self.call_fn(fn, args)
    def call_fn(self, fn, args):
        ce = Env(fn.env)
        for p, a in zip(fn.p, args): ce.define(p, Cell(a))
        try: self.xblock(fn.body, ce)
        except ReturnExc as r: return r.v
        return None

if __name__ == '__main__':
    with open(sys.argv[1]) as f: src = f.read()
    ast = Parser(tokenize(src)).program()
    interp = Interp()
    interp.run(ast)
    for l in interp.out: print(l)
