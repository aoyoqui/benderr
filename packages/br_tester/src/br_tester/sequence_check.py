import inspect
import ast
import textwrap
from typing import List, Type, get_args, get_origin
import numbers

def extract_steps_with_return(
    seq_cls: Type
) -> List[tuple[str, str]]:
    """
    Pull out every self.step(...) in seq_cls.sequence(), returning
    (step_name, return_type) with return_type in {"bool","numeric","str","none"}.
    Now handles negative numeric literals, and uses numbers.Number.
    """
    source = inspect.getsource(seq_cls.sequence)
    source = textwrap.dedent(source)
    tree = ast.parse(source)

    calls: List[tuple[str|None, ast.expr|None]] = []
    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and node.func.attr == "step"
            ):
                # capture optional name=
                custom = None
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        custom = kw.value.value
                        break
                pos = node.args[0] if node.args else None
                calls.append((custom, pos))
            self.generic_visit(node)

    Visitor().visit(tree)

    results: List[tuple[str, str]] = []
    for custom, pos in calls:
        # --- 1) determine step name ---
        if custom is not None:
            name = custom
        elif isinstance(pos, ast.Attribute):
            name = pos.attr
        elif isinstance(pos, ast.Name):
            name = pos.id
        elif isinstance(pos, ast.Lambda):
            name = "lambda"
        else:
            name = "none"

        # --- 2) determine return type ---
        ret_type = "none"

        # Helper to decide numeric from a Python value
        def _is_numeric_val(v):
            return isinstance(v, numbers.Number)

        # (A) Inline lambda
        if isinstance(pos, ast.Lambda):
            body = pos.body

            if isinstance(body, ast.Constant) and isinstance(body.value, bool):
                ret_type = "bool"
            elif isinstance(body, ast.Constant) and _is_numeric_val(body.value):
                ret_type = "numeric"
            elif (
                isinstance(body, ast.UnaryOp)
                and isinstance(body.op, ast.USub)
                and isinstance(body.operand, ast.Constant)
                and _is_numeric_val(body.operand.value)
            ):
                ret_type = "numeric"
            elif isinstance(body, ast.Constant) and isinstance(body.value, str):
                ret_type = "str"

        # (B) Named method: look at its annotation
        else:
            fn_name = None
            if isinstance(pos, ast.Attribute):
                fn_name = pos.attr
            elif isinstance(pos, ast.Name):
                fn_name = pos.id

            if fn_name:
                fn = getattr(seq_cls, fn_name, None)
                if fn:
                    ann = fn.__annotations__.get("return", None)
                    origin = get_origin(ann)
                    if origin is tuple:
                        args = get_args(ann)
                        ret_type = f"tuple[{', '.join(a.__name__ for a in args)}]"
                    elif ann is bool:
                        ret_type = "bool"
                    elif ann and issubclass(ann, numbers.Number):
                        ret_type = "numeric"
                    elif ann is str:
                        ret_type = "str"
                    elif isinstance(ann, type):
                        ret_type = ann.__name__

        results.append((name, ret_type))

    return results
