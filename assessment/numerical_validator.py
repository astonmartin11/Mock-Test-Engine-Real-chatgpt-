from __future__ import annotations
import sympy as sp

def verify_expression(expression: str, expected: float, tolerance: float=1e-6):
    try:
        value=float(sp.N(sp.sympify(expression)))
        return {'success':abs(value-expected)<=tolerance,'computed':value,'expected':expected,'difference':abs(value-expected)}
    except Exception as exc:
        return {'success':False,'computed':None,'expected':expected,'difference':None,'error':str(exc)}
