"""
马来西亚法定合规表格生成器 (Statutory Report Center)
═══════════════════════════════════════════════════════════════
真生成符合马来西亚国家级要求的 Excel 表格:
  · payslip       —— 工资单 (含 EPF/SOCSO/EIS/PCB 法定扣除明细)
  · epf_borang_a  —— EPF Borang A (KWSP 6) 月度公积金缴款表
  · ea_form       —— EA Form (C.P.8A) 年度个人薪酬扣税表 (Part A~F)
数据源: app.data.payroll_data
"""
from __future__ import annotations

import os
from datetime import datetime

from app.data import payroll_data as P

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# 全量法定表格定义池(各国从中按需引用;实际生成逻辑目前以 MY 为完整实现,
# 其余国家的国别专属表先登记清单,生成时回退到通用版式 + 国别抬头)
STATUTORY_FORMS = {
    # ── 通用 ──
    "payslip": ("工资单 Payslip", "Payslip"),
    "payroll_gl": ("薪资凭证分类账 · 借贷平衡", "Payroll GL Journal"),
    # ── 马来西亚 MY ──
    "epf_borang_a": ("EPF Borang A · 公积金缴款表", "EPF Borang A (KWSP 6)"),
    "ea_form": ("EA Form · 年度个税表", "Form EA (C.P.8A)"),
    "cp39": ("CP39 · PCB 月度汇缴表", "Form CP39 (LHDN MTD)"),
    "socso_8a": ("SOCSO Form 8A · 社保月报表", "SOCSO Form 8A (PERKESO)"),
    "bank_ibg": ("银行文件 IBG · 批量出粮", "Bank File IBG/GIRO (.txt)"),
    "lhdn_audit": ("LHDN 审计文件", "LHDN Audit File (.txt)"),
    "e_form": ("E 表 · 雇主年度申报", "Form E (Employer Annual Return)"),
    "ec_form": ("EC 表 · 雇员薪酬清单", "Form C.P.8D (EC / CP8D)"),
    # ── 新加坡 SG ──
    "ir8a": ("IR8A · 雇员年度入息表", "Form IR8A (Annual Return)"),
    "ir8a_appendix": ("Appendix 8A/8B · 附加福利表", "Appendix 8A/8B"),
    "ir21": ("IR21 · 离境清税表", "Form IR21 (Tax Clearance)"),
    "cpf_submission": ("CPF 缴款表", "CPF Contribution (CPF EZPay)"),
    "ais_file": ("AIS 自动入息申报文件", "Auto-Inclusion Scheme (AIS)"),
    # ── 泰国 TH ──
    "pnd1": ("PND.1 · 月度个税预扣表", "Form PND.1 (Monthly WHT)"),
    "pnd1_kor": ("PND.1 Kor · 年度个税汇总", "Form PND.1 Kor (Annual)"),
    "sso_kor_tor20": ("社保 SSO Kor.Tor.20", "SSO Kor.Tor.20"),
    "fiftytawi": ("50 Tawi · 扣缴凭证", "50 Tawi (WHT Certificate)"),
    # ── 越南 VN ──
    "pit_monthly": ("个税月报 (Mẫu 05/KK-TNCN)", "PIT Monthly (05/KK-TNCN)"),
    "pit_annual": ("个税年度结算 (Mẫu 05/QTT-TNCN)", "PIT Annual (05/QTT-TNCN)"),
    "si_d02": ("社保申报 D02-TS", "Social Insurance D02-TS"),
    # ── 印尼 ID ──
    "spt1721": ("SPT 1721 · 个税年度申报", "SPT Masa 1721 (PPh 21)"),
    "form_1721a1": ("1721-A1 · 雇员扣税凭证", "Form 1721-A1"),
    "bpjs": ("BPJS · 社保健康缴款表", "BPJS (Ketenagakerjaan/Kesehatan)"),
    # ── 香港 HK ──
    "ir56b": ("IR56B · 雇员薪酬通知书", "Form IR56B (Employer's Return)"),
    "ir56e": ("IR56E · 新雇员通知", "Form IR56E (New Employee)"),
    "ir56f": ("IR56F · 雇员离职通知", "Form IR56F (Cessation)"),
    "ir56g": ("IR56G · 离港雇员通知", "Form IR56G (Departure)"),
    "mpf_remittance": ("强积金 MPF 供款结算书", "MPF Remittance Statement"),
    # ── 中国 CN ──
    "iit_withholding": ("个税扣缴申报表", "IIT Withholding Return"),
    "iit_annual": ("个税年度汇算清缴", "IIT Annual Reconciliation"),
    "social_insurance": ("社保公积金缴纳明细", "Social Insurance & Housing Fund"),
}

# ── 各国法定报表清单(按 country code 大写)──
# 切换国家公司时,法定报表区只展示该国真实存在的表单
STATUTORY_FORMS_BY_COUNTRY = {
    "MY": ["payslip", "ea_form", "e_form", "ec_form", "epf_borang_a", "cp39",
           "socso_8a", "bank_ibg", "payroll_gl", "lhdn_audit"],
    "SG": ["payslip", "ir8a", "ir8a_appendix", "ir21", "cpf_submission",
           "ais_file", "payroll_gl"],
    "TH": ["payslip", "pnd1", "pnd1_kor", "sso_kor_tor20", "fiftytawi", "payroll_gl"],
    "VN": ["payslip", "pit_monthly", "pit_annual", "si_d02", "payroll_gl"],
    "ID": ["payslip", "spt1721", "form_1721a1", "bpjs", "payroll_gl"],
    "HK": ["payslip", "ir56b", "ir56e", "ir56f", "ir56g", "mpf_remittance", "payroll_gl"],
    "CN": ["payslip", "iit_withholding", "iit_annual", "social_insurance", "payroll_gl"],
}

# company.id(小写)→ country(大写)
def _country_of(company: str) -> str:
    try:
        from app.data import enterprise as _e
        for g in _e.GROUPS:
            for c in g["companies"]:
                if c.get("id") == (company or "").lower():
                    return c.get("country", "MY")
    except Exception:
        pass
    return (company or "MY").upper()

def forms_for_company(company: str = "my") -> list:
    """返回某公司所属国家的法定报表清单(切换公司即变)。"""
    country = _country_of(company)
    ids = STATUTORY_FORMS_BY_COUNTRY.get(country, STATUTORY_FORMS_BY_COUNTRY["MY"])
    return [{"id": fid, "name_zh": STATUTORY_FORMS[fid][0],
             "name_en": STATUTORY_FORMS[fid][1]} for fid in ids if fid in STATUTORY_FORMS]

# ── 薪资科目表(COA, FRS 第8节映射规则)──
COA = {
    "wage_exp":   ("61000", "工资费用 Wage Expense"),
    "ot_exp":     ("61001", "加班费 Overtime Expense"),
    "epf_exp":    ("62000", "EPF 费用 (雇主)"),
    "socso_exp":  ("62001", "SOCSO 费用 (雇主)"),
    "eis_exp":    ("62002", "EIS 费用 (雇主)"),
    "hrdf_exp":   ("62003", "HRDF 费用"),
    "pay_payable":("21000", "应付工资 Salary Payable"),
    "epf_pay":    ("22001", "应付 EPF"),
    "socso_pay":  ("22002", "应付 SOCSO"),
    "eis_pay":    ("22003", "应付 EIS"),
    "lhdn_pay":   ("22004", "应付 LHDN/PCB"),
    "hrdf_pay":   ("22005", "应付 HRDF"),
    "zakat_pay":  ("23001", "应付宗教捐 Zakat"),
    "ded_pay":    ("23002", "应付扣款 (贷款/PTPTN)"),
    "bank":       ("11001", "银行账户 Bank"),
}

# ── 样式常量 ──
_NAVY = "0F766E"
_TEAL = "20C997"
_GREY = "64748B"
_LIGHT = "F1F5F9"


def export_statutory(form_id: str, company: str = "my", period: str = "", emp_no: str = "") -> dict:
    if form_id not in STATUTORY_FORMS:
        return {"error": f"未知法定表格: {form_id}"}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 纯文本类(银行文件/LHDN审计)用 .txt,其余用 .xlsx
    ext = "txt" if form_id in ("bank_ibg", "lhdn_audit") else "xlsx"
    fname = f"{form_id}_{company}_{ts}.{ext}"
    path = os.path.join(EXPORT_DIR, fname)

    # 已有完整实现的表单(目前为通用 + 马来西亚)
    _IMPLEMENTED = {"payslip", "epf_borang_a", "ea_form", "cp39",
                    "socso_8a", "bank_ibg", "payroll_gl", "lhdn_audit"}

    extra = None
    if form_id == "payslip":
        _build_payslip(path, period or "2026-05", emp_no)
    elif form_id == "epf_borang_a":
        _build_epf_borang_a(path, period or "2026-05")
    elif form_id == "ea_form":
        _build_ea_form(path, period or "2026")
    elif form_id == "cp39":
        _build_cp39(path, period or "2026-05")
    elif form_id == "socso_8a":
        _build_socso_8a(path, period or "2026-05")
    elif form_id == "bank_ibg":
        extra = _build_bank_ibg(path, period or "2026-05")
    elif form_id == "payroll_gl":
        extra = _build_payroll_gl(path, period or "2026-05")
    elif form_id == "lhdn_audit":
        _build_lhdn_audit(path, period or "2026-05")
    else:
        # 其余国别专属表单:通用版式 + 正确的国别抬头(诚实标注未完成精算)
        _build_generic_country_form(path, form_id, company, period or "2026-05")

    out_extra = extra or {}
    return {"ok": True, "form_id": form_id, "filename": fname, **out_extra,
            "download_url": f"/api/report/download/{fname}",
            "size": os.path.getsize(path),
            "title": STATUTORY_FORMS[form_id][0]}


def _styles():
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    return {
        "title": Font(bold=True, size=16, color=_NAVY),
        "sub": Font(size=10, color=_GREY),
        "hfont": Font(bold=True, color="FFFFFF", size=10),
        "hfill": PatternFill("solid", fgColor=_TEAL),
        "label": Font(bold=True, color="334155", size=10),
        "money": Font(size=10),
        "bold": Font(bold=True, size=11, color=_NAVY),
        "light": PatternFill("solid", fgColor=_LIGHT),
        "center": Alignment(horizontal="center", vertical="center"),
        "right": Alignment(horizontal="right"),
        "wrap": Alignment(wrap_text=True, vertical="top"),
        "border": Border(*(Side(style="thin", color="CBD5E1"),) * 4),
    }


# ════════════════ ① Payslip 工资单 ════════════════
def _build_payslip(path: str, period: str, emp_no: str):
    from openpyxl import Workbook
    s = _styles()
    emps = P.PAYROLL_EMPLOYEES
    if emp_no:
        emps = [e for e in emps if e["emp_no"] == emp_no] or emps
    wb = Workbook()
    first = True
    for emp in emps:
        m = P.compute_monthly(emp)
        ws = wb.active if first else wb.create_sheet()
        ws.title = emp["emp_no"]
        first = False
        ws.column_dimensions["A"].width = 26
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 26
        ws.column_dimensions["D"].width = 16

        ws.merge_cells("A1:D1"); ws["A1"] = P.EMPLOYER["name"]; ws["A1"].font = s["title"]
        ws.merge_cells("A2:D2"); ws["A2"] = P.EMPLOYER["address"]; ws["A2"].font = s["sub"]
        ws.merge_cells("A3:D3"); ws["A3"] = f"PAYSLIP / 工资单 — {period}"; ws["A3"].font = s["bold"]

        ws["A5"] = "Employee / 员工"; ws["A5"].font = s["label"]; ws["B5"] = emp["name"]
        ws["C5"] = "Emp No / 工号"; ws["C5"].font = s["label"]; ws["D5"] = emp["emp_no"]
        ws["A6"] = "IC No / 身份证"; ws["A6"].font = s["label"]; ws["B6"] = emp["ic_no"]
        ws["C6"] = "Designation / 职位"; ws["C6"].font = s["label"]; ws["D6"] = emp["designation"]
        ws["A7"] = "EPF No / 公积金号"; ws["A7"].font = s["label"]; ws["B7"] = emp["epf_no"]
        ws["C7"] = "Dept / 部门"; ws["C7"].font = s["label"]; ws["D7"] = emp["dept"]

        # 收入 / 扣除 双栏
        r = 9
        ws.cell(r, 1, "EARNINGS / 收入").font = s["hfont"]; ws.cell(r, 1).fill = s["hfill"]
        ws.cell(r, 2, "RM").font = s["hfont"]; ws.cell(r, 2).fill = s["hfill"]
        ws.cell(r, 3, "DEDUCTIONS / 扣除").font = s["hfont"]; ws.cell(r, 3).fill = s["hfill"]
        ws.cell(r, 4, "RM").font = s["hfont"]; ws.cell(r, 4).fill = s["hfill"]

        earnings = [("Basic Salary 基本工资", emp["basic"]),
                    ("Fixed Allowance 固定津贴", emp.get("allow_fixed", 0)),
                    ("Overtime 加班费", emp.get("ot", 0)),
                    ("Tax-Exempt Allowance 免税津贴", emp.get("allow_taxexempt", 0))]
        deductions = [("EPF (Employee 11%) 公积金", m["epf_emp"]),
                      ("SOCSO 社险", m["socso_emp"]),
                      ("EIS 就业保险", m["eis_emp"]),
                      ("PCB (MTD) 月度预扣税", m["pcb"]),
                      ("Zakat 天课", m.get("zakat", 0))]
        for i in range(max(len(earnings), len(deductions))):
            rr = r + 1 + i
            if i < len(earnings):
                ws.cell(rr, 1, earnings[i][0]); ws.cell(rr, 2, earnings[i][1]).alignment = s["right"]
            if i < len(deductions):
                ws.cell(rr, 3, deductions[i][0]); ws.cell(rr, 4, deductions[i][1]).alignment = s["right"]

        tot = r + 1 + max(len(earnings), len(deductions))
        ws.cell(tot, 1, "Gross Pay 总收入").font = s["label"]
        ws.cell(tot, 2, m["gross_total"]).font = s["label"]; ws.cell(tot, 2).alignment = s["right"]
        ws.cell(tot, 3, "Total Deductions 总扣除").font = s["label"]
        ws.cell(tot, 4, m["total_deduction"]).font = s["label"]; ws.cell(tot, 4).alignment = s["right"]

        net = tot + 2
        ws.merge_cells(start_row=net, start_column=1, end_row=net, end_column=3)
        ws.cell(net, 1, "NET PAY / 实发净额 (RM)").font = s["bold"]
        ws.cell(net, 4, m["net_pay"]).font = s["bold"]; ws.cell(net, 4).alignment = s["right"]
        ws.cell(net, 4).fill = s["light"]

        er = net + 2
        ws.cell(er, 1, "Employer Contributions / 雇主缴款").font = s["sub"]
        ws.cell(er + 1, 1, f"EPF Employer: RM {m['epf_er']}  ·  SOCSO: RM {m['socso_er']}  ·  EIS: RM {m['eis_er']}").font = s["sub"]
        ws.cell(er + 3, 1, "本工资单依马来西亚 EPF/SOCSO/EIS/PCB 法定费率生成。正式申报请以 KWSP/PERKESO/LHDN 官方计算为准。").font = s["sub"]
    wb.save(path)


# ════════════════ ② EPF Borang A (KWSP 6) ════════════════
def _build_epf_borang_a(path: str, period: str):
    from openpyxl import Workbook
    s = _styles()
    wb = Workbook(); ws = wb.active; ws.title = "Borang A"
    widths = [6, 16, 28, 18, 14, 16, 16, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    ws.merge_cells("A1:H1"); ws["A1"] = "BORANG A (KWSP 6) — Monthly EPF Contribution / 公积金月度缴款表"
    ws["A1"].font = s["title"]
    ws.merge_cells("A2:H2"); ws["A2"] = f"Employer 雇主: {P.EMPLOYER['name']}  ·  EPF No 雇主号: {P.EMPLOYER['epf_no']}"
    ws["A2"].font = s["sub"]
    ws.merge_cells("A3:H3"); ws["A3"] = f"Contribution Month 缴款月份: {period}"
    ws["A3"].font = s["label"]

    headers = ["No", "EPF Member No\n会员号", "Employee Name\n姓名", "IC No\n身份证",
               "Wages (RM)\n工资", "Employee 11%\n雇员", "Employer\n雇主", "Total\n合计"]
    hr = 5
    for ci, h in enumerate(headers, 1):
        c = ws.cell(hr, ci, h); c.font = s["hfont"]; c.fill = s["hfill"]
        c.alignment = s["center"]; c.border = s["border"]

    tot_wage = tot_emp = tot_er = tot_all = 0.0
    for i, emp in enumerate(P.PAYROLL_EMPLOYEES, 1):
        m = P.compute_monthly(emp)
        total = round(m["epf_emp"] + m["epf_er"], 2)
        row = [i, emp["epf_no"], emp["name"], emp["ic_no"],
               m["gross_taxable"], m["epf_emp"], m["epf_er"], total]
        for ci, v in enumerate(row, 1):
            c = ws.cell(hr + i, ci, v); c.border = s["border"]
            if ci >= 5: c.alignment = s["right"]
        tot_wage += m["gross_taxable"]; tot_emp += m["epf_emp"]
        tot_er += m["epf_er"]; tot_all += total

    tr = hr + len(P.PAYROLL_EMPLOYEES) + 1
    ws.cell(tr, 4, "TOTAL 合计").font = s["label"]
    for ci, v in zip([5, 6, 7, 8], [tot_wage, round(tot_emp, 2), round(tot_er, 2), round(tot_all, 2)]):
        c = ws.cell(tr, ci, v); c.font = s["label"]; c.fill = s["light"]; c.alignment = s["right"]

    ws.cell(tr + 2, 1, f"Total Members 缴款人数: {len(P.PAYROLL_EMPLOYEES)}").font = s["sub"]
    ws.cell(tr + 3, 1, "Payment Due 缴款截止: 次月 15 日前 (on or before 15th of following month).").font = s["sub"]
    ws.cell(tr + 4, 1, "本表依 EPF 雇员11%/雇主13%(≤5000)或12%(>5000) 生成,正式提交请以 KWSP i-Akaun 为准。").font = s["sub"]
    wb.save(path)


# ════════════════ ③ EA Form (C.P.8A) ════════════════
def _build_ea_form(path: str, year: str):
    from openpyxl import Workbook
    s = _styles()
    wb = Workbook()
    first = True
    for emp in P.PAYROLL_EMPLOYEES:
        a = P.compute_annual(emp)
        ws = wb.active if first else wb.create_sheet()
        ws.title = emp["emp_no"]; first = False
        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 52
        ws.column_dimensions["C"].width = 18

        ws.merge_cells("A1:C1"); ws["A1"] = f"FORM EA (C.P.8A) — Year {year}"; ws["A1"].font = s["title"]
        ws.merge_cells("A2:C2"); ws["A2"] = "STATEMENT OF REMUNERATION FROM EMPLOYMENT / 雇员薪酬扣税表"
        ws["A2"].font = s["bold"]
        ws.merge_cells("A3:C3"); ws["A3"] = f"{P.EMPLOYER['name']}  ·  Employer No: {P.EMPLOYER['employer_no']}"
        ws["A3"].font = s["sub"]

        def section(r, txt):
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
            c = ws.cell(r, 1, txt); c.font = s["hfont"]; c.fill = s["hfill"]
        def line(r, no, label, val=None):
            if no: ws.cell(r, 1, no)
            ws.cell(r, 2, label)
            if val is not None:
                c = ws.cell(r, 3, val); c.alignment = s["right"]

        r = 5
        section(r, "PART A — Employee Particulars / 雇员资料"); r += 1
        line(r, "1", "Name 姓名", emp["name"]); r += 1
        line(r, "2", "Income Tax No / IC No 税号/身份证", emp["ic_no"]); r += 1
        line(r, "3", "EPF No 公积金号", emp["epf_no"]); r += 1
        line(r, "4", "Designation 职位", emp["designation"]); r += 1
        line(r, "5", "Employment Period 任职期间", f"01/01/{year} - 31/12/{year}"); r += 2

        section(r, "PART B — Gross Remuneration (Section 13(1)) / 总薪酬"); r += 1
        line(r, "1(a)", "Salary, wages, leave pay 薪资/工资/假期薪", a["annual_gross"] - a["annual_bonus"] - a["annual_ot"]); r += 1
        line(r, "1(b)", "Bonus / Gratuity 奖金/酬金", a["annual_bonus"]); r += 1
        line(r, "1(c)", "Overtime 加班费", a["annual_ot"]); r += 1
        line(r, "1(d)", "Director's fee 董事酬金", 0); r += 1
        line(r, "", "Sub-total Gross 总薪酬小计", a["annual_gross"]); ws.cell(r, 2).font = s["label"]; ws.cell(r, 3).font = s["label"]; r += 2

        section(r, "PART C — Benefits-in-Kind (BIK) & VOLA / 实物福利与住宿"); r += 1
        line(r, "1", "Benefits-in-Kind 实物福利", 0); r += 1
        line(r, "2", "Value of Living Accommodation (VOLA) 住宿价值", 0); r += 2

        section(r, "PART D — Pension & Others / 退休金及其他"); r += 1
        line(r, "1", "Pension / Annuity 退休金", 0); r += 1
        line(r, "2", "Compensation for loss of employment 离职补偿", 0); r += 2

        section(r, "PART E — Deductions / 扣除项"); r += 1
        line(r, "1", "MTD / PCB 月度预扣税合计", a["annual_pcb"]); r += 1
        line(r, "2", "EPF (Employee) 雇员公积金", a["annual_epf_emp"]); r += 1
        line(r, "3", "SOCSO 社险", a["annual_socso_emp"]); r += 1
        line(r, "4", "EIS 就业保险", a["annual_eis_emp"]); r += 1
        line(r, "5", "Zakat / Fitrah 天课", a.get("annual_zakat", 0)); r += 2

        section(r, "PART F — Tax-Exempt Allowances / 免税津贴"); r += 1
        line(r, "1", "Petrol / Travel Allowance 油费/交通津贴 (≤RM6,000)", min(a["annual_taxexempt"], 6000)); r += 1
        line(r, "2", "Childcare Allowance 托儿津贴 (≤RM2,400)", 0); r += 1
        line(r, "3", "Meal / Parking 餐补/停车", 0); r += 1
        line(r, "4", "Long Service Award 服务奖 (≤RM2,000)", 0); r += 2

        ws.cell(r, 1, "本表依 LHDN Form EA (C.P.8A) 结构生成,须于次年 2 月底前发予雇员。正式申报以 LHDN e-Filing / HASiL 官方为准。").font = s["sub"]
    wb.save(path)


# ════════════════ ④ CP39 (PCB 月度汇缴表) ════════════════
def _build_cp39(path: str, period: str):
    from openpyxl import Workbook
    s = _styles()
    wb = Workbook(); ws = wb.active; ws.title = "CP39"
    for i, w in enumerate([6, 18, 26, 18, 16, 14, 14, 16, 14], 1):
        ws.column_dimensions[chr(64 + i)].width = w

    ws.merge_cells("A1:I1"); ws["A1"] = "FORM CP39 — Monthly PCB/MTD Remittance / 月度预扣税汇缴表"
    ws["A1"].font = s["title"]
    ws.merge_cells("A2:I2"); ws["A2"] = f"Employer 雇主: {P.EMPLOYER['name']}  ·  Tax File 税档号: {P.EMPLOYER['employer_no']}"
    ws["A2"].font = s["sub"]
    ws.merge_cells("A3:I3"); ws["A3"] = f"Month/Year 月份: {period}  ·  Submission 提交日: {datetime.now():%d/%m/%Y}"
    ws["A3"].font = s["label"]

    headers = ["No\n序号", "Tax File\n税档号", "Employee Name\n姓名", "IC/Passport\n证件",
               "Remuneration\n月度报酬", "EPF\n公积金", "MTD/PCB\n当月", "YTD PCB\n累计", "Remark\n备注"]
    hr = 5
    for ci, h in enumerate(headers, 1):
        c = ws.cell(hr, ci, h); c.font = s["hfont"]; c.fill = s["hfill"]
        c.alignment = s["center"]; c.border = s["border"]

    n = tot_rem = tot_pcb = tot_ytd = 0
    tot_rem = tot_pcb = tot_ytd = 0.0
    for emp in P.PAYROLL_EMPLOYEES:
        m = P.compute_monthly(emp)
        if m["pcb"] <= 0:          # 仅含有 PCB 的员工(文档要求)
            continue
        n += 1
        ytd = round(m["pcb"] * 5, 2)   # 年初至今(演示: 假设第5个月)
        row = [n, emp.get("tax_no", ""), emp["name"], emp["ic_no"].replace("-", ""),
               m["gross_taxable"], m["epf_emp"], m["pcb"], ytd, ""]
        for ci, v in enumerate(row, 1):
            c = ws.cell(hr + n, ci, v); c.border = s["border"]
            if ci >= 5: c.alignment = s["right"]
        tot_rem += m["gross_taxable"]; tot_pcb += m["pcb"]; tot_ytd += ytd

    tr = hr + n + 1
    ws.cell(tr, 4, "TOTAL 合计").font = s["label"]
    for ci, v in zip([5, 7, 8], [round(tot_rem, 2), round(tot_pcb, 2), round(tot_ytd, 2)]):
        c = ws.cell(tr, ci, v); c.font = s["label"]; c.fill = s["light"]; c.alignment = s["right"]
    ws.cell(tr + 2, 1, f"Employees with PCB 缴税人数: {n}").font = s["sub"]
    ws.cell(tr + 3, 1, "Payment Due 缴款截止: 次月 15 日前. 关联表: CP21(离职)/CP22(入职)/CP22A(变更).").font = s["sub"]
    ws.cell(tr + 5, 1, "证明: 本人证明所提供信息真实准确。  签名: ______________  日期: __________  (公司盖章)").font = s["label"]
    ws.cell(tr + 7, 1, "本表依 LHDN CP39 结构生成,正式提交以 LHDN e-PCB / e-Data PCB 官方为准。").font = s["sub"]
    wb.save(path)


# ════════════════ ⑤ SOCSO Form 8A (社保月报表) ════════════════
def _build_socso_8a(path: str, period: str):
    from openpyxl import Workbook
    s = _styles()
    wb = Workbook(); ws = wb.active; ws.title = "SOCSO 8A"
    for i, w in enumerate([6, 16, 26, 18, 14, 14, 14, 14, 14], 1):
        ws.column_dimensions[chr(64 + i)].width = w

    ws.merge_cells("A1:I1"); ws["A1"] = "SOCSO FORM 8A — Monthly Contribution / 社险月度缴款表 (PERKESO)"
    ws["A1"].font = s["title"]
    ws.merge_cells("A2:I2"); ws["A2"] = f"Employer 雇主: {P.EMPLOYER['name']}  ·  SOCSO No 社保号: {P.EMPLOYER['socso_no']}"
    ws["A2"].font = s["sub"]
    ws.merge_cells("A3:I3"); ws["A3"] = f"Contribution Month 缴款月份: {period}  ·  Submission 提交日: {datetime.now():%d/%m/%Y}"
    ws["A3"].font = s["label"]

    headers = ["No", "SOCSO No\n社保号", "Employee Name\n姓名", "IC No\n身份证(无横线)",
               "Wages\n工资", "SIP Emp\n工伤员工", "SIP Er\n工伤雇主", "Emp Total\n员工合计", "Er Total\n雇主合计"]
    hr = 5
    for ci, h in enumerate(headers, 1):
        c = ws.cell(hr, ci, h); c.font = s["hfont"]; c.fill = s["hfill"]
        c.alignment = s["center"]; c.border = s["border"]

    n = 0
    t_wage = t_emp = t_er = 0.0
    for emp in P.PAYROLL_EMPLOYEES:
        m = P.compute_monthly(emp)
        n += 1
        # SIP(工伤) 与 SPK(残疾) 在一类计划中合并由 socso_employee/employer 给出
        emp_part = m["socso_emp"]; er_part = m["socso_er"]
        row = [n, emp.get("socso_no", ""), emp["name"], emp["ic_no"].replace("-", ""),
               m["gross_taxable"], emp_part, er_part, emp_part, er_part]
        for ci, v in enumerate(row, 1):
            c = ws.cell(hr + n, ci, v); c.border = s["border"]
            if ci >= 5: c.alignment = s["right"]
        t_wage += m["gross_taxable"]; t_emp += emp_part; t_er += er_part

    tr = hr + n + 1
    ws.cell(tr, 4, "TOTAL 合计").font = s["label"]
    for ci, v in zip([5, 8, 9], [round(t_wage, 2), round(t_emp, 2), round(t_er, 2)]):
        c = ws.cell(tr, ci, v); c.font = s["label"]; c.fill = s["light"]; c.alignment = s["right"]
    grand = round(t_emp + t_er, 2)
    ws.cell(tr + 2, 1, f"员工总数: {n}   员工总额: {round(t_emp,2)}   雇主总额: {round(t_er,2)}   总计(员工+雇主): {grand}").font = s["label"]
    ws.cell(tr + 3, 1, "付款方式: ☐支票 ☐电子转账 ☐其他   参考号: ______________").font = s["sub"]
    ws.cell(tr + 5, 1, "本表依 PERKESO Form 8A 结构生成,正式提交以 ASSIST Portal 官方为准。").font = s["sub"]
    wb.save(path)


# ════════════════ ⑥ 银行文件 IBG/GIRO (.txt 定长) ════════════════
def _build_bank_ibg(path: str, period: str) -> dict:
    """生成 IBG 定长文本: 表头(类型1,80) + 明细(类型2,100) + 表尾(类型9,80)。"""
    emps = [P.compute_monthly(e) for e in P.PAYROLL_EMPLOYEES]
    details = [e for e in emps if e.get("bank_acct")]
    proc_date = datetime.now().strftime("%d%m%Y")
    batch_ref = "PAY" + datetime.now().strftime("%y%m%d%H%M")
    total_amt = round(sum(e["net_pay"] for e in details), 2)
    period_tag = period.replace("-", "").upper()

    def amt15(x):  # 15位右对齐, 含2位小数无符号
        return f"{x:.2f}".replace(".", "").rjust(15, "0")[:15]
    def amt_hdr(x):
        return f"{x:.2f}".replace(".", "").rjust(15, "0")[:15]

    lines = []
    # 表头(类型1) — 固定 80 字符
    hdr = ("1" + "IBG" + "MBB" + P.EMPLOYER.get("epf_no", "")[:10].ljust(10)
           + P.EMPLOYER["name"][:40].ljust(40) + proc_date + batch_ref[:12].ljust(12)
           + str(len(details)).rjust(6, "0") + amt_hdr(total_amt))
    lines.append(hdr.ljust(80)[:80])
    # 明细(类型2) — 固定 100 字符
    hash_tail = 0
    for e in details:
        acct = (e.get("bank_acct", "") or "")
        hash_tail += int(acct[-4:]) if acct[-4:].isdigit() else 0
        ref = f"PAYDAES-SAL-{period_tag}"
        det = ("2" + (e.get("bank_code", "") or "")[:3].ljust(3) + "000"
               + acct.rjust(20, "0")[:20] + e["name"][:40].ljust(40)
               + amt15(e["net_pay"]) + ref[:20].ljust(20) + "03" + " ")
        lines.append(det.ljust(100)[:100])
    # 表尾(类型9) — 固定 80 字符
    ftr = ("9" + str(len(details) + 2).rjust(6, "0") + amt_hdr(total_amt)
           + str(hash_tail).rjust(12, "0"))
    lines.append(ftr.ljust(80)[:80])

    with open(path, "w", encoding="ascii", errors="replace") as f:
        f.write("\n".join(lines) + "\n")
    return {"batch_ref": batch_ref, "txn_count": len(details), "total_amount": total_amt}


# ════════════════ ⑦ 薪资凭证分类账 (借贷平衡) ════════════════
def build_payroll_journal(period: str) -> dict:
    """构建薪资凭证(分录),严格借贷平衡。返回 {voucher_no, lines[], total_debit, total_credit, balanced}。"""
    emps = [P.compute_monthly(e) for e in P.PAYROLL_EMPLOYEES]
    agg = {
        # 工资费用 = 总收入扣除加班部分(加班单列): basic + 津贴(应税+免税) + 奖金 + 佣金
        "wage": sum(e["gross_total"] - e["ot_amount"] for e in emps),
        "ot": sum(e["ot_amount"] for e in emps),
        "epf_emp": sum(e["epf_emp"] for e in emps),  "epf_er": sum(e["epf_er"] for e in emps),
        "socso_emp": sum(e["socso_emp"] for e in emps), "socso_er": sum(e["socso_er"] for e in emps),
        "eis_emp": sum(e["eis_emp"] for e in emps),  "eis_er": sum(e["eis_er"] for e in emps),
        "hrdf": sum(e["hrdf"] for e in emps),
        "pcb": sum(e["pcb"] for e in emps), "zakat": sum(e.get("zakat", 0) for e in emps),
        "net": sum(e["net_pay"] for e in emps),
    }
    agg = {k: round(v, 2) for k, v in agg.items()}
    n = len(emps)
    L = []  # (code, name, debit, credit, ref)
    def dr(key, amt, ref=""):
        c, nm = COA[key]; L.append([c, nm, round(amt, 2), 0.0, ref])
    def cr(key, amt, ref=""):
        c, nm = COA[key]; L.append([c, nm, 0.0, round(amt, 2), ref])

    # 借: 费用类
    dr("wage_exp", agg["wage"], f"{n} 名员工 工资+津贴")
    if agg["ot"]: dr("ot_exp", agg["ot"], "加班费")
    dr("epf_exp", agg["epf_er"], "雇主 EPF")
    dr("socso_exp", agg["socso_er"], "雇主 SOCSO")
    dr("eis_exp", agg["eis_er"], "雇主 EIS")
    if agg["hrdf"]: dr("hrdf_exp", agg["hrdf"], "HRDF 征费")
    # 贷: 应付各项 + 实发(走应付工资过渡再贷银行)
    cr("epf_pay", round(agg["epf_emp"] + agg["epf_er"], 2), "应付 EPF (员工+雇主)")
    cr("socso_pay", round(agg["socso_emp"] + agg["socso_er"], 2), "应付 SOCSO")
    cr("eis_pay", round(agg["eis_emp"] + agg["eis_er"], 2), "应付 EIS")
    cr("lhdn_pay", agg["pcb"], "应付 PCB/LHDN")
    if agg["hrdf"]: cr("hrdf_pay", agg["hrdf"], "应付 HRDF")
    if agg["zakat"]: cr("zakat_pay", agg["zakat"], "应付 Zakat")
    cr("bank", agg["net"], "实发工资 → 银行")

    total_debit = round(sum(x[2] for x in L), 2)
    total_credit = round(sum(x[3] for x in L), 2)
    # 借贷平衡保护: 浮点尾差兜底(<=0.05 调入银行行)
    diff = round(total_debit - total_credit, 2)
    if abs(diff) > 0 and abs(diff) <= 0.05:
        for x in L:
            if x[1].startswith("银行账户"):
                x[3] = round(x[3] + diff, 2); break
        total_credit = round(sum(x[3] for x in L), 2)
    voucher_no = f"PAY-{period.replace('-', '-')}-0001"
    return {"voucher_no": voucher_no, "period": period, "lines": L,
            "total_debit": round(total_debit, 2), "total_credit": round(total_credit, 2),
            "balanced": abs(total_debit - total_credit) < 0.01, "emp_count": n}


def _build_payroll_gl(path: str, period: str) -> dict:
    from openpyxl import Workbook
    s = _styles()
    j = build_payroll_journal(period)
    wb = Workbook(); ws = wb.active; ws.title = "GL Journal"
    for i, w in enumerate([8, 14, 30, 16, 16, 28], 1):
        ws.column_dimensions[chr(64 + i)].width = w

    ws.merge_cells("A1:F1"); ws["A1"] = "PAYROLL JOURNAL — 薪资凭证分类账 (借贷平衡)"; ws["A1"].font = s["title"]
    ws.merge_cells("A2:F2"); ws["A2"] = f"Voucher 凭证编号: {j['voucher_no']}  ·  Period 期间: {period}  ·  Source 来源: 薪资"
    ws["A2"].font = s["sub"]
    ws.merge_cells("A3:F3"); ws["A3"] = f"摘要: {period} 薪资凭证  ·  状态: 草稿  ·  过账日: {datetime.now():%Y-%m-%d %H:%M}"
    ws["A3"].font = s["label"]

    headers = ["Line\n行号", "Account\n科目编码", "Account Name\n科目名称", "Debit\n借方", "Credit\n贷方", "Reference\n参考"]
    hr = 5
    for ci, h in enumerate(headers, 1):
        c = ws.cell(hr, ci, h); c.font = s["hfont"]; c.fill = s["hfill"]
        c.alignment = s["center"]; c.border = s["border"]
    for i, (code, name, dr, cr, ref) in enumerate(j["lines"], 1):
        row = [i, code, name, dr if dr else None, cr if cr else None, ref]
        for ci, v in enumerate(row, 1):
            c = ws.cell(hr + i, ci, v); c.border = s["border"]
            if ci in (4, 5): c.alignment = s["right"]
    tr = hr + len(j["lines"]) + 1
    ws.cell(tr, 3, "控制合计 TOTAL").font = s["label"]
    c = ws.cell(tr, 4, j["total_debit"]); c.font = s["label"]; c.fill = s["light"]; c.alignment = s["right"]
    c = ws.cell(tr, 5, j["total_credit"]); c.font = s["label"]; c.fill = s["light"]; c.alignment = s["right"]
    bal = "✓ 借贷平衡 BALANCED" if j["balanced"] else "✗ 不平衡 — 请检查"
    ws.cell(tr + 2, 1, f"借方总额 {j['total_debit']}  =  贷方总额 {j['total_credit']}   {bal}").font = s["bold"]
    ws.cell(tr + 3, 1, "规则: 借方必须等于贷方(会计平衡原则); 每笔凭证至少2行。COA 可转换至本地科目表。").font = s["sub"]
    wb.save(path)
    return {"voucher_no": j["voucher_no"], "balanced": j["balanced"],
            "total_debit": j["total_debit"], "total_credit": j["total_credit"]}


# ════════════════ ⑧ LHDN 审计文件 (.txt) ════════════════
def _build_lhdn_audit(path: str, period: str):
    emps = [P.compute_monthly(e) for e in P.PAYROLL_EMPLOYEES]
    lines = []
    lines.append("=" * 78)
    lines.append("LHDN AUDIT FILE / LHDN 审计文件".center(78))
    lines.append(f"Employer: {P.EMPLOYER['name']}".ljust(78))
    lines.append(f"Tax File: {P.EMPLOYER['employer_no']}   Period: {period}".ljust(78))
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}".ljust(78))
    lines.append("=" * 78)
    hdr = f"{'TaxFile':<12}{'Name':<22}{'IC':<16}{'Gross':>12}{'EPF':>10}{'PCB':>10}"
    lines.append(hdr)
    lines.append("-" * 78)
    t_gross = t_epf = t_pcb = 0.0
    for e in emps:
        lines.append(f"{e.get('tax_no',''):<12}{e['name'][:21]:<22}{e['ic_no'].replace('-',''):<16}"
                     f"{e['gross_taxable']:>12.2f}{e['epf_emp']:>10.2f}{e['pcb']:>10.2f}")
        t_gross += e["gross_taxable"]; t_epf += e["epf_emp"]; t_pcb += e["pcb"]
    lines.append("-" * 78)
    lines.append(f"{'TOTAL':<50}{t_gross:>12.2f}{t_epf:>10.2f}{t_pcb:>10.2f}")
    lines.append("=" * 78)
    lines.append("本文件依 LHDN 审计要求生成(纯文本存档)。正式以 LHDN HASiL 官方格式为准。")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ════════════════ 通用国别法定表单(SG/TH/VN/ID/HK/CN 等) ════════════════
# 国别税务抬头信息(币种 / 税务局 / 社保机构)
_COUNTRY_META = {
    "SG": ("SGD", "IRAS · Inland Revenue Authority of Singapore", "CPF Board"),
    "TH": ("THB", "RD · Revenue Department", "SSO 社会保障办公室"),
    "VN": ("VND", "GDT · General Department of Taxation", "VSS 越南社会保险"),
    "ID": ("IDR", "DJP · Direktorat Jenderal Pajak", "BPJS"),
    "HK": ("HKD", "IRD · Inland Revenue Department", "MPFA 强积金管理局"),
    "CN": ("CNY", "国家税务总局 STA", "社保 / 公积金中心"),
    "MY": ("MYR", "LHDN · Lembaga Hasil Dalam Negeri", "KWSP / PERKESO"),
}

def _build_generic_country_form(path: str, form_id: str, company: str, period: str):
    """国别专属法定表单的通用生成器:正确国别抬头 + 员工薪资明细 + 合规声明。
    用于尚未做国别精算实现的表单,确保切换国家后导出不报错且抬头正确。"""
    from openpyxl import Workbook
    cy = _country_of(company)
    cur, tax_auth, social = _COUNTRY_META.get(cy, _COUNTRY_META["MY"])
    title_zh, title_en = STATUTORY_FORMS.get(form_id, (form_id, form_id))
    s = _styles()

    wb = Workbook(); ws = wb.active; ws.title = form_id[:28]
    ws.merge_cells("A1:F1"); ws["A1"] = f"{title_en} / {title_zh}"
    ws["A1"].font = s["title"]
    ws.merge_cells("A2:F2"); ws["A2"] = f"国家/Country: {cy}    主管机关/Authority: {tax_auth}"
    ws["A2"].font = s["sub"]
    ws.merge_cells("A3:F3"); ws["A3"] = f"所属期/Period: {period}    币种/Currency: {cur}    社保机构: {social}"
    ws["A3"].font = s["sub"]

    # 员工薪资明细(取真实薪资数据源)
    try:
        emps = P.PAYROLL_EMPLOYEES
    except Exception:
        emps = []
    hdr = ["No", "员工/Employee", "税号/TaxID", f"应税薪酬/Gross ({cur})", f"个税/Tax ({cur})", f"净额/Net ({cur})"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(5, j, h); c.font = s["hfont"]; c.fill = s["hfill"]
    r = 6; tg = tt = tn = 0.0
    for i, e in enumerate(emps, 1):
        try:
            m = P.compute_monthly(e)
        except Exception:
            m = e
        g = float(m.get("gross_taxable", 0) or 0)
        tax = float(m.get("pcb", 0) or 0)
        net = float(m.get("net_pay", g - tax) or (g - tax))
        ws.cell(r, 1, i); ws.cell(r, 2, e.get("name", "")); ws.cell(r, 3, e.get("tax_no", ""))
        ws.cell(r, 4, round(g, 2)); ws.cell(r, 5, round(tax, 2)); ws.cell(r, 6, round(net, 2))
        tg += g; tt += tax; tn += net; r += 1
    ws.cell(r, 2, "合计 TOTAL").font = s["hfont"]
    ws.cell(r, 4, round(tg, 2)); ws.cell(r, 5, round(tt, 2)); ws.cell(r, 6, round(tn, 2))

    note_r = r + 2
    ws.merge_cells(f"A{note_r}:F{note_r}")
    ws.cell(note_r, 1, f"⚠️ 本表为 {cy} 国别法定表单({title_en})的合规框架版,抬头与申报机关已按所属国适配；"
                       f"国别专属税率精算与官方版式正在按路线图逐国落地,正式申报请以 {tax_auth} 官方系统为准。").font = s["sub"]
    wb.save(path)
