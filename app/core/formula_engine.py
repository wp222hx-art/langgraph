"""
Paydaes 公式引擎 —— 假期资格 / 加班倍率 / 做账分录等业务规则的真实计算内核。

设计目标:
  • 安全: 不使用 Python eval/exec, 用自建 Tokenizer + Pratt 解析器 + 求值器,
    只放行白名单运算符与函数, 杜绝任意代码执行。
  • 业务贴合: 支持 HR/财务公式常见语法 ——
      - 算术:  + - * / %
      - 比较:  =  ==  !=  <>  <  <=  >  >=
      - 逻辑:  AND  OR  NOT  (大小写不敏感)
      - 函数:  IF(cond, a, b)  ROUND(x[, n])  MIN(...)  MAX(...)  ABS(x)  CEIL(x)  FLOOR(x)
      - 变量:  HR.GENDER  SERVICE.YEARS  ENTITLEMENT.DAYS ... (点号命名空间)
      - 字面量: 数字 / 'string' / "string" / TRUE / FALSE
  • 健壮: 变量值即使是字符串("7")也能参与数值比较/算术(自动转 number)。
  • 可解释: 返回 {ok, result, result_type, type, used_vars, error} ——
    既给最终值, 也给变量代入快照, 便于前端"算给你看"。

被 /api/formula/eval 调用; 也可被假期/薪资批算逻辑复用。
"""
from __future__ import annotations

import math
import re
from typing import Any

# ── 1. Tokenizer ──────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"""
    \s*(?:
      (?P<num>\d+\.\d+|\.\d+|\d+)                      # 数字
    | (?P<str>'[^']*'|"[^"]*")                          # 字符串字面量
    | (?P<op><=|>=|<>|!=|==|=|<|>|\+|\-|\*|/|%)          # 运算符(多字符在前)
    | (?P<lp>\()
    | (?P<rp>\))
    | (?P<comma>,)
    | (?P<name>[A-Za-z_][A-Za-z0-9_\.]*)                # 标识符/函数/变量/关键字
    )
""", re.VERBOSE)

_KEYWORDS = {"AND", "OR", "NOT", "TRUE", "FALSE"}
_FUNCS = {"IF", "ROUND", "MIN", "MAX", "ABS", "CEIL", "FLOOR", "AND", "OR", "NOT"}


class FormulaError(Exception):
    pass


def _tokenize(src: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos, n = 0, len(src)
    while pos < n:
        m = _TOKEN_RE.match(src, pos)
        if not m or m.end() == pos:
            if src[pos:].strip() == "":
                break
            raise FormulaError(f"无法识别的字符: '{src[pos:pos+12]}'")
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "name" and val.upper() in _KEYWORDS:
            tokens.append(("kw", val.upper()))
        else:
            tokens.append((kind, val))
    tokens.append(("eof", ""))
    return tokens


# ── 2. Pratt 解析器 → AST ─────────────────────────────────────────────────
class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.toks = tokens
        self.i = 0

    def _peek(self):
        return self.toks[self.i]

    def _next(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def _expect(self, kind, val=None):
        k, v = self._next()
        if k != kind or (val is not None and v != val):
            raise FormulaError(f"语法错误: 期望 {val or kind}, 实际 '{v}'")
        return v

    def parse(self):
        node = self._parse_or()
        if self._peek()[0] != "eof":
            raise FormulaError(f"多余的输入: '{self._peek()[1]}'")
        return node

    def _parse_or(self):
        node = self._parse_and()
        while self._peek() == ("kw", "OR"):
            self._next()
            node = ("binop", "OR", node, self._parse_and())
        return node

    def _parse_and(self):
        node = self._parse_not()
        while self._peek() == ("kw", "AND"):
            self._next()
            node = ("binop", "AND", node, self._parse_not())
        return node

    def _parse_not(self):
        if self._peek() == ("kw", "NOT"):
            self._next()
            return ("unary", "NOT", self._parse_not())
        return self._parse_cmp()

    def _parse_cmp(self):
        node = self._parse_add()
        while self._peek()[0] == "op" and self._peek()[1] in ("=", "==", "!=", "<>", "<", "<=", ">", ">="):
            op = self._next()[1]
            node = ("binop", op, node, self._parse_add())
        return node

    def _parse_add(self):
        node = self._parse_mul()
        while self._peek()[0] == "op" and self._peek()[1] in ("+", "-"):
            op = self._next()[1]
            node = ("binop", op, node, self._parse_mul())
        return node

    def _parse_mul(self):
        node = self._parse_unary()
        while self._peek()[0] == "op" and self._peek()[1] in ("*", "/", "%"):
            op = self._next()[1]
            node = ("binop", op, node, self._parse_unary())
        return node

    def _parse_unary(self):
        if self._peek()[0] == "op" and self._peek()[1] in ("+", "-"):
            op = self._next()[1]
            return ("unary", op, self._parse_unary())
        return self._parse_atom()

    def _parse_atom(self):
        k, v = self._peek()
        if k == "num":
            self._next()
            return ("num", float(v))
        if k == "str":
            self._next()
            return ("str", v[1:-1])
        if k == "kw" and v in ("TRUE", "FALSE"):
            self._next()
            return ("bool", v == "TRUE")
        if k == "lp":
            self._next()
            node = self._parse_or()
            self._expect("rp")
            return node
        if k == "name":
            self._next()
            if self._peek()[0] == "lp":          # 函数调用
                self._next()
                args = []
                if self._peek()[0] != "rp":
                    args.append(self._parse_or())
                    while self._peek()[0] == "comma":
                        self._next()
                        args.append(self._parse_or())
                self._expect("rp")
                return ("call", v.upper(), args)
            return ("var", v)
        raise FormulaError(f"无法解析: '{v or k}'")


# ── 3. 求值器 ──────────────────────────────────────────────────────────────
def _to_num(x: Any) -> float:
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        try:
            return float(s)
        except ValueError:
            raise FormulaError(f"无法把 '{x}' 当作数字参与计算")
    raise FormulaError(f"不支持的数值类型: {type(x).__name__}")


def _truthy(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0
    if isinstance(x, str):
        return x.strip() not in ("", "0", "false", "FALSE", "no", "No", "NO")
    return bool(x)


def _loose_eq(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    try:
        return _to_num(a) == _to_num(b)
    except FormulaError:
        return str(a).strip().lower() == str(b).strip().lower()


def _eval(node, env: dict, used: dict):
    t = node[0]
    if t == "num":
        return node[1]
    if t == "str":
        return node[1]
    if t == "bool":
        return node[1]
    if t == "var":
        name = node[1]
        for k in (name, name.upper(), name.lower()):
            if k in env:
                used[name] = env[k]
                return env[k]
        raise FormulaError(f"未提供变量值: {name}")
    if t == "unary":
        op = node[1]
        sub = _eval(node[2], env, used)
        if op == "-":
            return -_to_num(sub)
        if op == "+":
            return _to_num(sub)
        if op == "NOT":
            return not _truthy(sub)
    if t == "binop":
        op = node[1]
        if op == "AND":
            return _truthy(_eval(node[2], env, used)) and _truthy(_eval(node[3], env, used))
        if op == "OR":
            return _truthy(_eval(node[2], env, used)) or _truthy(_eval(node[3], env, used))
        a = _eval(node[2], env, used)
        b = _eval(node[3], env, used)
        if op in ("=", "=="):
            return _loose_eq(a, b)
        if op in ("!=", "<>"):
            return not _loose_eq(a, b)
        if op in ("<", "<=", ">", ">="):
            an, bn = _to_num(a), _to_num(b)
            return {"<": an < bn, "<=": an <= bn, ">": an > bn, ">=": an >= bn}[op]
        an, bn = _to_num(a), _to_num(b)
        if op == "+":
            return an + bn
        if op == "-":
            return an - bn
        if op == "*":
            return an * bn
        if op == "/":
            if bn == 0:
                raise FormulaError("除数不能为 0")
            return an / bn
        if op == "%":
            if bn == 0:
                raise FormulaError("取模的除数不能为 0")
            return an % bn
    if t == "call":
        return _call_func(node[1], node[2], env, used)
    raise FormulaError(f"无法求值的节点: {t}")


def _call_func(fname: str, args: list, env: dict, used: dict):
    if fname == "IF":
        if len(args) != 3:
            raise FormulaError("IF 需要 3 个参数: IF(条件, 真值, 假值)")
        cond = _truthy(_eval(args[0], env, used))
        return _eval(args[1] if cond else args[2], env, used)
    if fname == "ROUND":
        if not (1 <= len(args) <= 2):
            raise FormulaError("ROUND 需要 1~2 个参数")
        x = _to_num(_eval(args[0], env, used))
        n = int(_to_num(_eval(args[1], env, used))) if len(args) == 2 else 0
        return round(x, n)
    if fname in ("MIN", "MAX"):
        if not args:
            raise FormulaError(f"{fname} 至少需要 1 个参数")
        vals = [_to_num(_eval(a, env, used)) for a in args]
        return min(vals) if fname == "MIN" else max(vals)
    if fname == "ABS":
        return abs(_to_num(_eval(args[0], env, used)))
    if fname == "CEIL":
        return float(math.ceil(_to_num(_eval(args[0], env, used))))
    if fname == "FLOOR":
        return float(math.floor(_to_num(_eval(args[0], env, used))))
    if fname == "AND":
        return all(_truthy(_eval(a, env, used)) for a in args)
    if fname == "OR":
        return any(_truthy(_eval(a, env, used)) for a in args)
    if fname == "NOT":
        return not _truthy(_eval(args[0], env, used))
    raise FormulaError(f"未知函数: {fname}()")


# ── 4. 对外 API ──────────────────────────────────────────────────────────
def extract_vars(formula: str) -> list[str]:
    """从公式中抽出所有变量名(去掉函数名/关键字), 供前端预填表单。"""
    out: list[str] = []
    try:
        for k, v in _tokenize(formula):
            if k == "name" and v.upper() not in _FUNCS and v.upper() not in _KEYWORDS:
                if v not in out:
                    out.append(v)
    except FormulaError:
        pass
    return out


def evaluate(formula: str, variables: dict | None = None) -> dict:
    """
    计算公式。返回(同时含 result_type 与 type 以向后兼容):
      {ok: True,  result, result_type, type, used_vars, formula}
      {ok: False, error, formula}
    """
    formula = (formula or "").strip()
    if not formula:
        return {"ok": False, "error": "公式为空", "formula": formula}
    env: dict = {}
    for k, v in (variables or {}).items():
        if isinstance(v, str):
            s = v.strip()
            try:
                env[k] = float(s)
            except ValueError:
                env[k] = v
        else:
            env[k] = v
    try:
        ast_root = _Parser(_tokenize(formula)).parse()
        used: dict = {}
        result = _eval(ast_root, env, used)
        if isinstance(result, bool):
            rtype = "boolean"
        elif isinstance(result, (int, float)):
            rtype = "number"
            if float(result).is_integer():
                result = int(result)
        else:
            rtype = "text"
        return {
            "ok": True,
            "result": result,
            "result_type": rtype,
            "type": rtype,           # 向后兼容旧调用方
            "used_vars": used,
            "formula": formula,
        }
    except FormulaError as e:
        return {"ok": False, "error": str(e), "formula": formula}
    except Exception as e:           # 兜底, 不暴露内部栈
        return {"ok": False, "error": f"计算失败: {e}", "formula": formula}


# ── 5. 各业务域默认变量样例(供前端"试算"填充示例上下文) ──────────────────
SAMPLE_CONTEXTS = {
    "leave_entitlement": {
        "HR.GENDER": "M", "HR.MARITAL": "married",
        "SERVICE.YEARS": 6, "ENTITLEMENT.DAYS": 14, "AGE": 35, "HR.GRADE": "P6",
    },
    "overtime": {
        "OT.HOURS": 3, "RATE.NORMAL": 1.5, "RATE.HOLIDAY": 3.0,
        "IS.HOLIDAY": 0, "BASE.HOURLY": 25,
    },
    "default": {
        "BASE": 100, "RATE": 1.5, "DAYS": 10, "YEARS": 3,
        "AMOUNT": 5000, "QTY": 2,
    },
}


def sample_context(module_id: str = "default") -> dict:
    return dict(SAMPLE_CONTEXTS.get(module_id, SAMPLE_CONTEXTS["default"]))
