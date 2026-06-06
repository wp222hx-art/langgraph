"""
真实业务计算引擎 —— 把"硬编码 dict"换成"真正算出来的数"。

涵盖四类真实计算:
  1) 汇率换算   to_base_currency() —— 多币种 → 公司本位币(真实交叉汇率)
  2) 可抵扣税额 deductible_tax()  —— 按国别真实税率从价内税反算
  3) 限额校验   validate_limit()   —— 真比对报销类型单笔限额
  4) 风险评分   risk_score()       —— 多因子加权算分,而非写死"低/中/高"

所有税率来源于 enterprise.COUNTRIES(各国真实 GST/VAT/SST/PPN 口径)。
汇率为可维护的基准表(以 CNY 为锚的中间价),支持任意两币种交叉换算。
"""
from __future__ import annotations

import re

# ── 以 CNY 为锚的基准汇率(1 外币 = ? CNY) ──
# 真实量级口径,生产环境可由 forex_api 定时刷新这张表。
FX_TO_CNY = {
    "CNY": 1.0,
    "USD": 7.18,
    "EUR": 7.82,
    "HKD": 0.92,
    "JPY": 0.048,
    "GBP": 9.15,
    "SGD": 5.32,
    "MYR": 1.62,
    "THB": 0.205,
    "VND": 0.00029,
    "IDR": 0.00044,
}

# ── 各公司所在国(用于取税率) ──
_COMPANY_COUNTRY = {
    "sg": "SG", "my": "MY", "th": "TH", "vn": "VN",
    "id": "ID", "hk": "HK", "cn": "CN",
}


def fx_rate(frm: str, to: str) -> float:
    """任意两币种交叉汇率:1 单位 frm = ? to。"""
    frm, to = frm.upper(), to.upper()
    a = FX_TO_CNY.get(frm)
    b = FX_TO_CNY.get(to)
    if not a or not b:
        return 1.0
    return round(a / b, 6)


def to_base_currency(amount: float, frm: str, to: str) -> float:
    """把 amount(币种 frm)换算为本位币 to,保留 2 位。"""
    return round(amount * fx_rate(frm, to), 2)


def _tax_rate_pct(company: str) -> float:
    """取公司所在国真实税率(百分比小数,如 0.09)。"""
    from app.data import enterprise
    country = _COMPANY_COUNTRY.get(company, "CN")
    info = enterprise.COUNTRIES.get(country, {})
    raw = str(info.get("tax", {}).get("rate", "0%"))
    # 解析 "9%" / "6%/13%"(取最高档)/ "0%"
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*%", raw)
    if not nums:
        return 0.0
    return max(float(n) for n in nums) / 100.0


def deductible_tax(amount_base: float, company: str) -> float:
    """
    从价内含税金额反算可抵扣税额(真实进项税逻辑):
      含税额 = 不含税额 × (1 + r)  →  税额 = 含税额 × r / (1 + r)
    """
    r = _tax_rate_pct(company)
    if r <= 0:
        return 0.0
    return round(amount_base * r / (1 + r), 2)


def tax_info(company: str) -> dict:
    """返回公司适用税种与税率(供前端展示真实税务口径)。"""
    from app.data import enterprise
    country = _COMPANY_COUNTRY.get(company, "CN")
    info = enterprise.COUNTRIES.get(country, {})
    tax = info.get("tax", {})
    return {
        "country": country,
        "name": tax.get("name", ""),
        "rate": tax.get("rate", "0%"),
        "rate_pct": _tax_rate_pct(company),
        "authority": tax.get("authority", ""),
    }


def validate_limit(amount: float, limit_amt: float, type_name: str = "") -> dict:
    """真实限额校验。返回是否通过 + 超额信息。"""
    issues = []
    passed = True
    if limit_amt and amount > limit_amt:
        passed = False
        over = round(amount - limit_amt, 2)
        issues.append({
            "code": "OVER_LIMIT",
            "zh": f"金额 {amount} 超过【{type_name}】单笔限额 {limit_amt}(超 {over})",
            "en": f"Amount {amount} exceeds {type_name} per-claim limit {limit_amt} (over {over})",
        })
    return {"passed": passed, "issues": issues, "limit": limit_amt, "exceed_amt":
            round(max(0, amount - limit_amt), 2) if limit_amt else 0}


def risk_score(amount: float, limit_amt: float = 0, exceed: bool | None = None,
               weekend: bool = False, round_number: bool | None = None,
               no_invoice: bool = False) -> dict:
    """
    多因子真实风险评分(0-99),而非写死等级:
      - 超限:权重最高
      - 大额 / 超大额:阶梯加权
      - 整数金额(常见伪造特征)
      - 缺发票
    """
    score = 8
    reasons_zh, reasons_en = [], []

    if exceed is None:
        exceed = bool(limit_amt) and amount > limit_amt
    if exceed:
        score += 45
        reasons_zh.append("超过单笔限额")
        reasons_en.append("Exceeds per-claim limit")

    if amount > 3000:
        score += 22
        reasons_zh.append("超大额报销")
        reasons_en.append("Very large amount")
    elif amount > 1000:
        score += 14
        reasons_zh.append("大额报销")
        reasons_en.append("Large amount")

    if round_number is None:
        round_number = amount >= 100 and float(amount).is_integer() and amount % 100 == 0
    if round_number:
        score += 10
        reasons_zh.append("整百金额(异常特征)")
        reasons_en.append("Round-hundred amount (anomaly)")

    if no_invoice:
        score += 18
        reasons_zh.append("缺少发票")
        reasons_en.append("Missing invoice")

    if weekend:
        score += 6
        reasons_zh.append("周末消费")
        reasons_en.append("Weekend spend")

    score = min(score, 99)
    level = "低" if score < 30 else ("中" if score < 60 else "高")
    level_en = "Low" if score < 30 else ("Mid" if score < 60 else "High")
    if not reasons_zh:
        reasons_zh = ["无明显风险"]
        reasons_en = ["No obvious risk"]
    return {"score": score, "level": level, "level_en": level_en,
            "reasons": reasons_zh, "reasons_en": reasons_en}


def parse_amount(text: str) -> float | None:
    """从自然语言里抽金额:'打车花了88块' → 88.0。"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块|rmb|RMB|\$|sgd|SGD|myr|MYR)?", text)
    return float(m.group(1)) if m else None


def guess_type(text: str, company: str = "sg") -> dict | None:
    """关键词→报销类型(为 OCR 缺失时的本地兜底分类,真表里取限额)。"""
    from app.data import db
    rules = [
        (["打车", "滴滴", "taxi", "出租", "交通", "高铁", "火车", "train"], "TAXI"),
        (["餐", "饭", "吃", "meal", "聚餐", "宴", "咖啡"], "MEAL"),
        (["酒店", "住宿", "hotel", "住"], "HOTEL"),
        (["机票", "航班", "flight", "飞"], "FLIGHT"),
        (["办公", "文具", "office", "电脑", "京东"], "OFFICE"),
    ]
    t = text.lower()
    for kws, code in rules:
        if any(k.lower() in t for k in kws):
            return db.get_claim_type(code, company)
    return None
