"""
企业级数据层 —— 多集团/多公司、多角色、东南亚多国合规体系
支撑"集团性、专业级、全球化"的产品形态。
"""
from __future__ import annotations

# ═══════════════════════════════════════════════
# 多集团 / 多公司(多租户)
# ═══════════════════════════════════════════════
GROUPS = [
    {
        "id": "paydaes", "name": "Paydaes 集团", "name_en": "Paydaes Group",
        "logo": "P", "color": "#20c997", "plan": "Enterprise",
        "companies": [
            {"id": "sg", "name": "新加坡公司", "name_en": "Singapore Pte Ltd", "country": "SG", "flag": "🇸🇬", "currency": "SGD", "employees": 320, "active": True},
            {"id": "my", "name": "马来西亚公司", "name_en": "Malaysia Sdn Bhd", "country": "MY", "flag": "🇲🇾", "currency": "MYR", "employees": 256, "active": True},
            {"id": "th", "name": "泰国公司", "name_en": "Thailand Co., Ltd", "country": "TH", "flag": "🇹🇭", "currency": "THB", "employees": 198, "active": True},
            {"id": "vn", "name": "越南公司", "name_en": "Vietnam Co., Ltd", "country": "VN", "flag": "🇻🇳", "currency": "VND", "employees": 174, "active": True},
            {"id": "id", "name": "印尼公司", "name_en": "Indonesia PT", "country": "ID", "flag": "🇮🇩", "currency": "IDR", "employees": 412, "active": True},
        ],
    },
    {
        "id": "horizon", "name": "Horizon 控股", "name_en": "Horizon Holdings",
        "logo": "H", "color": "#0891b2", "plan": "Enterprise",
        "companies": [
            {"id": "hk", "name": "香港公司", "name_en": "Hong Kong Ltd", "country": "HK", "flag": "🇭🇰", "currency": "HKD", "employees": 88, "active": True},
            {"id": "cn", "name": "中国公司", "name_en": "China Co., Ltd", "country": "CN", "flag": "🇨🇳", "currency": "CNY", "employees": 560, "active": True},
        ],
    },
]

# ═══════════════════════════════════════════════
# 四层 / 六大角色权限模型
# ═══════════════════════════════════════════════
ROLES = [
    {"id": "employee", "name": "普通员工", "name_en": "Employee", "icon": "fa-user", "color": "#10b981",
     "desc": "提交查看个人报销/差旅、维护家庭信息",
     "menus": ["dashboard", "my", "global"]},
    {"id": "approver", "name": "审批人", "name_en": "Approver", "icon": "fa-user-check", "color": "#3b82f6",
     "desc": "审批/退回/批量操作管辖范围报销",
     "menus": ["dashboard", "my", "claim_data", "global"]},
    {"id": "hr_admin", "name": "HR 管理员", "name_en": "HR Admin", "icon": "fa-user-gear", "color": "#8b5cf6",
     "desc": "规则配置、权益批量生成、代员工提交",
     "menus": ["dashboard", "settings", "my", "claim_data", "claim_flow", "report", "hr", "tax", "leave", "ta", "accounting", "master", "global"]},
    {"id": "payroll", "name": "薪资专员", "name_en": "Payroll Officer", "icon": "fa-money-check-dollar", "color": "#f59e0b",
     "desc": "接口流程、过账、审核接口数据",
     "menus": ["dashboard", "claim_flow", "audit", "report", "global"]},
    {"id": "finance", "name": "财务/审计", "name_en": "Finance/Audit", "icon": "fa-scale-balanced", "color": "#ec4899",
     "desc": "余额调整、查看所有分析报表",
     "menus": ["dashboard", "audit", "report", "global"]},
    {"id": "sys_admin", "name": "系统管理员", "name_en": "System Admin", "icon": "fa-shield-halved", "color": "#64748b",
     "desc": "全模块权限、角色及租户配置",
     "menus": ["dashboard", "settings", "my", "claim_data", "claim_flow", "audit", "report", "hr", "tax", "leave", "ta", "accounting", "master", "global"]},
]

# ═══════════════════════════════════════════════
# 东南亚多国合规体系(税收 / 报销 / 做账)
# ═══════════════════════════════════════════════
COUNTRIES = {
    "SG": {
        "name": "新加坡", "name_en": "Singapore", "flag": "🇸🇬", "currency": "SGD", "lang": "en",
        "tax": {"name": "GST 商品服务税", "rate": "9%", "authority": "IRAS 新加坡税务局", "filing": "季度申报 (GST F5)"},
        "claim_rules": ["餐饮可抵扣 GST", "需保留 5 年税务凭证", "客户招待费部分不可抵扣"],
        "accounting": {"standard": "SFRS 新加坡财务报告准则", "fiscal": "可自选财年", "elements": ["6100-差旅费", "6200-餐饮费", "6300-办公费"]},
    },
    "MY": {
        "name": "马来西亚", "name_en": "Malaysia", "flag": "🇲🇾", "currency": "MYR", "lang": "ms",
        "tax": {"name": "SST 销售服务税", "rate": "6%", "authority": "LHDN 马来西亚税务局", "filing": "双月申报 (SST-02)"},
        "claim_rules": ["服务税适用于特定服务", "需电子发票 e-Invoice (2024强制)", "里程补贴有上限"],
        "accounting": {"standard": "MFRS 马来西亚财务报告准则", "fiscal": "12 个月", "elements": ["6100-Perjalanan", "6200-Makanan", "6300-Pejabat"]},
    },
    "TH": {
        "name": "泰国", "name_en": "Thailand", "flag": "🇹🇭", "currency": "THB", "lang": "th",
        "tax": {"name": "VAT 增值税", "rate": "7%", "authority": "RD 泰国税务厅", "filing": "月度申报 (PP30)"},
        "claim_rules": ["完整税票需含 13 位税号", "差旅每日津贴免税额度", "外币需按央行汇率换算"],
        "accounting": {"standard": "TFRS 泰国财务报告准则", "fiscal": "12 个月", "elements": ["6100-ค่าเดินทาง", "6200-ค่าอาหาร", "6300-สำนักงาน"]},
    },
    "VN": {
        "name": "越南", "name_en": "Vietnam", "flag": "🇻🇳", "currency": "VND", "lang": "vi",
        "tax": {"name": "VAT 增值税", "rate": "10%", "authority": "GDT 越南税务总局", "filing": "月度/季度申报"},
        "claim_rules": ["需红色发票 (VAT Invoice)", "电子发票强制", "现金报销超 2000万盾不可抵扣"],
        "accounting": {"standard": "VAS 越南会计准则", "fiscal": "12 个月", "elements": ["6420-Chi phí đi lại", "6422-Ăn uống", "6423-Văn phòng"]},
    },
    "ID": {
        "name": "印尼", "name_en": "Indonesia", "flag": "🇮🇩", "currency": "IDR", "lang": "id",
        "tax": {"name": "PPN 增值税", "rate": "11%", "authority": "DJP 印尼税务总局", "filing": "月度申报 (SPT Masa)"},
        "claim_rules": ["需税务发票 Faktur Pajak", "NPWP 税号必填", "招待费限额抵扣"],
        "accounting": {"standard": "PSAK 印尼财务会计准则", "fiscal": "12 个月", "elements": ["6100-Biaya Perjalanan", "6200-Konsumsi", "6300-Kantor"]},
    },
    "HK": {
        "name": "香港", "name_en": "Hong Kong", "flag": "🇭🇰", "currency": "HKD", "lang": "zh",
        "tax": {"name": "无销售税/增值税", "rate": "0%", "authority": "IRD 香港税务局", "filing": "年度利得税"},
        "claim_rules": ["无 GST/VAT", "保留单据 7 年", "雇员福利需申报"],
        "accounting": {"standard": "HKFRS 香港财务报告准则", "fiscal": "可自选", "elements": ["6100-差旅", "6200-膳食", "6300-办公"]},
    },
    "CN": {
        "name": "中国", "name_en": "China", "flag": "🇨🇳", "currency": "CNY", "lang": "zh",
        "tax": {"name": "增值税 VAT", "rate": "6%/13%", "authority": "国家税务总局", "filing": "月度申报"},
        "claim_rules": ["需增值税专用发票方可抵扣", "发票查验真伪", "电子发票合规"],
        "accounting": {"standard": "CAS 企业会计准则", "fiscal": "自然年", "elements": ["6601-差旅费", "6602-业务招待费", "6603-办公费"]},
    },
}

# 多语言(界面文案)
I18N = {
    "zh": {"dashboard": "工作台", "settings": "设置", "my": "我的", "claim": "报销", "report": "报表", "hr": "核心HR", "global": "全球合规"},
    "en": {"dashboard": "Dashboard", "settings": "Settings", "my": "My Space", "claim": "Claims", "report": "Reports", "hr": "Core HR", "global": "Compliance"},
}

LANGUAGES = [
    {"code": "zh", "name": "简体中文", "flag": "🇨🇳"},
    {"code": "en", "name": "English", "flag": "🇬🇧"},
    {"code": "ms", "name": "Bahasa Melayu", "flag": "🇲🇾"},
    {"code": "th", "name": "ไทย", "flag": "🇹🇭"},
    {"code": "vi", "name": "Tiếng Việt", "flag": "🇻🇳"},
    {"code": "id", "name": "Bahasa Indonesia", "flag": "🇮🇩"},
]
