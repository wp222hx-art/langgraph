"""
员工薪资名单 Excel 导入引擎
═══════════════════════════════════════════════════════════════
为「合规报表中心」提供真实员工薪资名单的导入能力:
  1. 生成标准导入模板(带表头说明 + 示例行 + 数据校验提示)
  2. 解析上传的 .xlsx
  3. 逐行校验(必填/类型/枚举/IC格式/数值范围)
  4. 返回结构化预览(成功行 + 错误清单),便于前端确认后再落地

字段与 payroll_data._emp() 完全对齐,导入后即可直接喂给 pcb_engine 精确计算。
"""
from __future__ import annotations

import io
import os
import re
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.core import reporting  # 复用 EXPORT_DIR

EXPORT_DIR = reporting.EXPORT_DIR

# ── 导入列定义(顺序即模板列顺序) ──
# (key, 中文表头, 英文表头, 是否必填, 类型, 说明/枚举)
COLUMNS = [
    ("emp_no",            "员工编号*",        "Emp No*",          True,  "str",  "唯一,如 MY001"),
    ("name",              "姓名*",            "Name*",            True,  "str",  "与身份证一致"),
    ("ic_no",             "身份证号*",        "IC No*",           True,  "ic",   "格式 880512-14-5523"),
    ("epf_no",            "EPF会员号",        "EPF No",           False, "str",  "KWSP 会员号"),
    ("socso_no",          "SOCSO号",          "SOCSO No",         False, "str",  "PERKESO 号"),
    ("designation",       "职位",             "Designation",      False, "str",  ""),
    ("dept",              "部门",             "Dept",             False, "str",  ""),
    ("basic",             "基本月薪*",        "Basic Salary*",    True,  "num",  "RM,>0"),
    ("allow_fixed",       "应税固定津贴",     "Taxable Allow",    False, "num",  "RM"),
    ("allow_taxexempt",   "免税津贴",         "Tax-Exempt Allow", False, "num",  "RM,EA Part F"),
    ("bonus",             "年度奖金",         "Annual Bonus",     False, "num",  "RM"),
    ("ot",                "月度加班费",       "Monthly OT",       False, "num",  "RM"),
    ("marital",           "婚姻状况",         "Marital",          False, "enum", "single/married"),
    ("spouse_income",     "配偶有收入",       "Spouse Has Income",False, "bool", "Y/N(已婚必填)"),
    ("children",          "普通子女数",       "Children",         False, "int",  "整数"),
    ("children_tertiary", "高教子女数",       "Tertiary Children",False, "int",  "整数(享RM8000宽免)"),
    ("zakat_monthly",     "月度Zakat",        "Monthly Zakat",    False, "num",  "RM"),
    ("tp1_relief",        "TP1其他年度宽免",  "TP1 Other Relief", False, "num",  "RM(医疗/教育/生活方式等)"),
]

KEYS = [c[0] for c in COLUMNS]
REQUIRED = [c[0] for c in COLUMNS if c[3]]
MARITAL_ENUM = {"single", "married"}
IC_RE = re.compile(r"^\d{6}-\d{2}-\d{4}$")

_EXAMPLE = [
    "MY001", "Ahmad Bin Ismail", "880512-14-5523", "12345601", "880512145523",
    "Engineering Manager", "Technology", 9500, 1200, 500, 19000, 0,
    "married", "N", 2, 0, 150, 0,
]


# ════════════════════ 1. 模板生成 ════════════════════
def build_template() -> dict:
    """生成标准导入模板 .xlsx(说明页 + 数据页 + 示例行)。"""
    wb = Workbook()

    # ── 说明页 ──
    ws0 = wb.active
    ws0.title = "说明 Instructions"
    title_f = Font(bold=True, size=14, color="1F4E78")
    head_f = Font(bold=True, size=11, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="2E5395")
    ws0["A1"] = "员工薪资名单导入模板 · Employee Payroll Import Template"
    ws0["A1"].font = title_f
    ws0["A2"] = "Paydaes ClaimGPT · 合规报表中心 (Payslip / EPF Borang A / EA Form 数据源)"
    ws0["A2"].font = Font(italic=True, color="808080")
    notes = [
        "",
        "填写须知:",
        "1. 请在「数据 Data」页填写,第 1 行为表头(请勿删除),第 2 行为示例(可覆盖或删除)。",
        "2. 带 * 的列为必填:员工编号、姓名、身份证号、基本月薪。",
        "3. 身份证号格式: YYMMDD-PB-###G (例 880512-14-5523)。",
        "4. 婚姻状况填 single 或 married;已婚请填「配偶有收入」(Y=有 / N=无)。",
        "   · 配偶无收入(N) 可享 RM4,000 配偶宽免,直接影响 PCB。",
        "5. 子女宽免: 普通子女每名 RM2,000;高教子女每名 RM8,000。",
        "6. 月度 Zakat 会按 LHDN 规则从 PCB 中抵扣。",
        "7. TP1 其他年度宽免: 医疗/教育保险、生活方式、SSPN 等,填年度总额。",
        "8. 金额单位均为 RM,只填数字(勿带货币符号/逗号)。",
        "9. 填写完成后,在系统「合规报表中心 → 导入员工名单」上传本文件即可。",
        "",
        "费率依据 2024 马来西亚标准(KWSP/PERKESO/LHDN),正式申报以官方为准。",
    ]
    r = 3
    for n in notes:
        ws0.cell(r, 1, n)
        if n.endswith(":"):
            ws0.cell(r, 1).font = Font(bold=True, color="C00000")
        r += 1
    ws0.column_dimensions["A"].width = 90

    # ── 数据页 ──
    ws = wb.create_sheet("数据 Data")
    thin = Side(style="thin", color="BBBBBB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for ci, col in enumerate(COLUMNS, start=1):
        key, zh, en, req, typ, hint = col
        cell = ws.cell(1, ci, f"{zh}\n{en}")
        cell.font = head_f
        cell.fill = PatternFill("solid", fgColor="C00000" if req else "2E5395")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        # 示例行
        ex = ws.cell(2, ci, _EXAMPLE[ci - 1])
        ex.font = Font(italic=True, color="808080")
        ex.border = border
        # 列宽
        ws.column_dimensions[ws.cell(1, ci).column_letter].width = max(12, len(zh) + 4)
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"

    fname = f"payroll_import_template_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, fname)
    wb.save(path)
    return {
        "ok": True,
        "filename": fname,
        "download_url": f"/api/report/download/{fname}",
        "size": os.path.getsize(path),
        "title": "员工薪资名单导入模板",
    }


# ════════════════════ 2. 解析 + 校验 ════════════════════
def _to_num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("RM", "").strip()
    return float(s)


def _to_int(v):
    if v is None or v == "":
        return 0
    return int(round(_to_num(v)))


def _to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"y", "yes", "true", "1", "有"}


def parse_and_validate(content: bytes) -> dict:
    """解析上传的 xlsx 字节流,逐行校验,返回 {ok, rows, errors, summary}。"""
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception as e:
        return {"ok": False, "error": f"无法读取 Excel 文件: {e}"}

    # 优先取「数据 Data」页,否则取第一个有数据的页
    ws = wb["数据 Data"] if "数据 Data" in wb.sheetnames else wb[wb.sheetnames[0]]

    rows_out, errors = [], []
    seen_emp_no = set()
    data_rows = 0

    for ri, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        # 跳过示例行(emp_no=MY001 且 name=Ahmad Bin Ismail 的纯示例)
        cells = list(row) + [None] * (len(KEYS) - len(row))
        rec = {KEYS[i]: cells[i] for i in range(len(KEYS))}
        data_rows += 1
        row_errs = []

        # 必填校验
        for k in REQUIRED:
            if rec.get(k) is None or str(rec.get(k)).strip() == "":
                row_errs.append(f"{k} 必填")

        emp_no = str(rec.get("emp_no") or "").strip()
        if emp_no:
            if emp_no in seen_emp_no:
                row_errs.append(f"员工编号 {emp_no} 重复")
            seen_emp_no.add(emp_no)

        # IC 格式
        ic = str(rec.get("ic_no") or "").strip()
        if ic and not IC_RE.match(ic):
            row_errs.append(f"身份证号格式应为 880512-14-5523,实得「{ic}」")

        # 数值
        try:
            basic = _to_num(rec.get("basic"))
            if basic <= 0:
                row_errs.append("基本月薪需 > 0")
        except Exception:
            basic = 0.0
            row_errs.append(f"基本月薪非数字「{rec.get('basic')}」")

        # 婚姻枚举
        marital = str(rec.get("marital") or "single").strip().lower()
        if marital not in MARITAL_ENUM:
            row_errs.append(f"婚姻状况应为 single/married,实得「{rec.get('marital')}」")
            marital = "single"

        # 组装规范化记录(对齐 _emp 字段)
        try:
            norm = dict(
                emp_no=emp_no,
                name=str(rec.get("name") or "").strip(),
                ic_no=ic,
                epf_no=str(rec.get("epf_no") or "").strip(),
                socso_no=str(rec.get("socso_no") or "").strip(),
                designation=str(rec.get("designation") or "").strip(),
                dept=str(rec.get("dept") or "").strip(),
                basic=basic,
                allow_fixed=_to_num(rec.get("allow_fixed")),
                allow_taxexempt=_to_num(rec.get("allow_taxexempt")),
                bonus=_to_num(rec.get("bonus")),
                ot=_to_num(rec.get("ot")),
                marital=marital,
                spouse_income=_to_bool(rec.get("spouse_income")) if marital == "married" else True,
                children=_to_int(rec.get("children")),
                children_tertiary=_to_int(rec.get("children_tertiary")),
                zakat_monthly=_to_num(rec.get("zakat_monthly")),
                tp1_relief=_to_num(rec.get("tp1_relief")),
            )
        except Exception as e:
            row_errs.append(f"数值解析失败: {e}")
            norm = None

        if row_errs:
            errors.append({"row": ri, "emp_no": emp_no or f"(第{ri}行)", "errors": row_errs})
        elif norm:
            rows_out.append(norm)

    # 用精确引擎试算 PCB,生成预览(只对通过校验的行)
    preview = []
    if rows_out:
        from app.data import payroll_data as pd
        for emp in rows_out:
            try:
                m = pd.compute_monthly(emp)
                preview.append({
                    "emp_no": emp["emp_no"], "name": emp["name"],
                    "gross": m.get("gross_total", m.get("gross_taxable", 0)),
                    "epf_emp": m["epf_emp"],
                    "pcb": m["pcb"], "zakat": m.get("zakat", 0),
                    "net": m.get("net_pay", 0),
                })
            except Exception as e:
                errors.append({"row": "-", "emp_no": emp["emp_no"], "errors": [f"试算失败: {e}"]})

    return {
        "ok": len(errors) == 0,
        "rows": rows_out,
        "preview": preview,
        "errors": errors,
        "summary": {
            "data_rows": data_rows,
            "valid": len(rows_out),
            "invalid": len(errors),
        },
    }
