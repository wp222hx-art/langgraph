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

STATUTORY_FORMS = {
    "payslip": ("工资单 Payslip", "Payslip"),
    "epf_borang_a": ("EPF Borang A · 公积金缴款表", "EPF Borang A (KWSP 6)"),
    "ea_form": ("EA Form · 年度个税表", "Form EA (C.P.8A)"),
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
    fname = f"{form_id}_{company}_{ts}.xlsx"
    path = os.path.join(EXPORT_DIR, fname)

    if form_id == "payslip":
        _build_payslip(path, period or "2026-05", emp_no)
    elif form_id == "epf_borang_a":
        _build_epf_borang_a(path, period or "2026-05")
    elif form_id == "ea_form":
        _build_ea_form(path, period or "2026")

    return {"ok": True, "form_id": form_id, "filename": fname,
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
