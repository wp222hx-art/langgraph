"""
Mock 数据层 —— MVP 阶段用内存模拟数据库。
阶段二会替换为 Supabase(Postgres + pgvector)。
覆盖 18 模块所需的核心业务数据。
"""
from __future__ import annotations

import random

# ① 报销类型
CLAIM_TYPES = [
    {"code": "MEAL", "name": "餐饮费", "limit": 200, "need_invoice": True, "group": "日常"},
    {"code": "TAXI", "name": "交通费", "limit": 500, "need_invoice": True, "group": "日常"},
    {"code": "HOTEL", "name": "住宿费", "limit": 800, "need_invoice": True, "group": "差旅"},
    {"code": "FLIGHT", "name": "机票", "limit": 5000, "need_invoice": True, "group": "差旅"},
    {"code": "OFFICE", "name": "办公用品", "limit": 1000, "need_invoice": True, "group": "日常"},
    {"code": "TRAIN", "name": "高铁/火车", "limit": 2000, "need_invoice": True, "group": "差旅"},
]

# ② 报销组
CLAIM_GROUPS = ["日常", "差旅", "福利", "培训"]

# ③ 报销权益 / 员工权益余额
ENTITLEMENTS = {
    "E001": {"name": "张伟", "dept": "技术部", "annual": 30000, "used": 8600, "level": "P7"},
    "E002": {"name": "李娜", "dept": "市场部", "annual": 25000, "used": 19200, "level": "P6"},
    "E003": {"name": "王芳", "dept": "财务部", "annual": 20000, "used": 3400, "level": "P5"},
}

# ④ 汇率(模拟实时,后台自动)
EXCHANGE_RATES = {"USD": 7.18, "EUR": 7.82, "HKD": 0.92, "JPY": 0.048, "GBP": 9.15}

# ⑧⑨⑩ 待审批单据(管理端)
PENDING_CLAIMS = [
    {"id": "C20260601", "user": "张伟", "type": "餐饮费", "amount": 186, "risk": "低", "note": "团队聚餐"},
    {"id": "C20260602", "user": "李娜", "type": "机票", "amount": 4200, "risk": "中", "note": "上海出差"},
    {"id": "C20260603", "user": "王芳", "type": "住宿费", "amount": 1500, "risk": "高", "note": "超标准2晚"},
    {"id": "C20260604", "user": "张伟", "type": "交通费", "amount": 88, "risk": "低", "note": "打车"},
    {"id": "C20260605", "user": "李娜", "type": "餐饮费", "amount": 980, "risk": "高", "note": "单笔超限"},
]

# ⑱ 家庭信息
FAMILY = {
    "E001": [{"relation": "配偶", "name": "刘敏"}, {"relation": "子女", "name": "张小宝"}],
    "E002": [{"relation": "父亲", "name": "李建国"}],
}


def mock_ocr_invoice() -> dict:
    """模拟发票 OCR 抽取结果"""
    samples = [
        {"merchant": "海底捞火锅", "category": "餐饮费", "amount": 386.00, "date": "2026-06-05", "tax_no": "91310000XXX"},
        {"merchant": "滴滴出行", "category": "交通费", "amount": 47.50, "date": "2026-06-05", "tax_no": "91110000YYY"},
        {"merchant": "全季酒店", "category": "住宿费", "amount": 459.00, "date": "2026-06-04", "tax_no": "91440000ZZZ"},
        {"merchant": "京东商城", "category": "办公用品", "amount": 1280.00, "date": "2026-06-03", "tax_no": "91110000AAA"},
    ]
    return random.choice(samples)


def mock_report_data(kind: str) -> dict:
    """模拟报表/洞察数据"""
    if "差旅" in kind:
        return {
            "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
            "series": [{"name": "差旅支出(万)", "data": [12, 15, 9, 18, 22, 16]}],
            "insight": "差旅支出 5 月达峰值 22 万,环比增 22%,主要由华东区出差激增驱动。",
        }
    if "福利" in kind:
        return {
            "labels": ["餐饮", "交通", "住宿", "培训", "体检"],
            "series": [{"name": "福利使用率(%)", "data": [86, 72, 65, 40, 91]}],
            "insight": "体检福利使用率最高(91%),培训福利偏低(40%),建议加强培训权益宣导。",
        }
    return {
        "labels": ["技术部", "市场部", "财务部", "运营部"],
        "series": [{"name": "报销总额(万)", "data": [45, 62, 18, 33]}],
        "insight": "市场部报销额最高(62万),技术部次之。建议关注市场部餐饮费占比。",
    }


def get_balance(emp_id: str = "E001") -> dict:
    e = ENTITLEMENTS.get(emp_id, ENTITLEMENTS["E001"])
    return {**e, "remaining": e["annual"] - e["used"]}
