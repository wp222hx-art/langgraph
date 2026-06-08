"""
EA Form (C.P.8A) 官方 PDF 版式生成器
═══════════════════════════════════════════════════════════════
还原 LEMBAGA HASIL DALAM NEGERI MALAYSIA (HASiL/LHDN) 的
「PENYATA SARAAN DARIPADA PENGGAJIAN / Statement of Remuneration
from Employment for the Year」官方双语版式(Borang C.P.8A)。

雇主须于次年 2 月底前发给每位雇员,供其填报个人所得税(BE/B 表)。
本模块依官方 Part A~F 结构逐项排版,每位雇员生成一页。
"""
from __future__ import annotations

import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.core import reporting
from app.data import payroll_data as pd

EXPORT_DIR = reporting.EXPORT_DIR

NAVY = colors.HexColor("#0B2E59")
GREY = colors.HexColor("#5b6470")
LINE = colors.HexColor("#9aa3ad")
HEAD_FILL = colors.HexColor("#0B2E59")
SUB_FILL = colors.HexColor("#dbe4f0")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "gov":   ParagraphStyle("gov", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=11, textColor=NAVY, alignment=TA_CENTER, leading=14),
        "formno": ParagraphStyle("formno", parent=ss["Normal"], fontName="Helvetica-Bold",
                                 fontSize=9, textColor=colors.black, alignment=TA_CENTER),
        "title": ParagraphStyle("title", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=9.5, textColor=colors.black, alignment=TA_CENTER, leading=12),
        "sub":   ParagraphStyle("sub", parent=ss["Normal"], fontName="Helvetica-Oblique",
                                fontSize=7.5, textColor=GREY, alignment=TA_CENTER, leading=9),
        "sec":   ParagraphStyle("sec", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, textColor=colors.white, leading=11),
        "lbl":   ParagraphStyle("lbl", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=7.8, textColor=colors.black, leading=10),
        "lblb":  ParagraphStyle("lblb", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=7.8, textColor=colors.black, leading=10),
        "val":   ParagraphStyle("val", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=7.8, textColor=colors.black, alignment=TA_LEFT, leading=10),
        "foot":  ParagraphStyle("foot", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=6.8, textColor=GREY, leading=9),
    }


def _rm(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return "0.00"


def _section_bar(text, S, width):
    """蓝底白字的分节标题条。"""
    t = Table([[Paragraph(text, S["sec"])]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HEAD_FILL),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _kv_table(rows, S, width, money_col=False):
    """两/三列明细表: [编号, 标签(双语), 金额]。"""
    data = []
    for r in rows:
        no, label_bm, label_en, val = r
        lbl = Paragraph(f"<b>{label_bm}</b><br/><font color='#5b6470' size=6.8>{label_en}</font>", S["lbl"])
        valcell = Paragraph(_rm(val) if val is not None else "", S["val"]) if money_col else \
            Paragraph(str(val) if val is not None else "", S["val"])
        data.append([Paragraph(no, S["lblb"]), lbl, valcell])
    col = [12 * mm, width - 12 * mm - 36 * mm, 36 * mm]
    t = Table(data, colWidths=col)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f4f8")),
    ]))
    return t


def _emp_page(a, year, employer, S, width):
    """单个雇员的 EA Form 页面元素列表。"""
    el = []
    # ── 页眉:政府抬头 + 表号 ──
    hdr = Table([[
        Paragraph("LEMBAGA HASIL DALAM NEGERI MALAYSIA<br/>"
                  "<font size=7.5 color='#5b6470'>INLAND REVENUE BOARD OF MALAYSIA</font>", S["gov"]),
        Paragraph("Borang<br/><b>C.P.8A</b><br/>"
                  "<font size=6.5 color='#5b6470'>Pin. 2024</font>", S["formno"]),
    ]], colWidths=[width - 28 * mm, 28 * mm])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (1, 0), (1, 0), 0.8, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))
    el.append(hdr)
    el.append(Spacer(1, 4))
    el.append(Paragraph(
        "PENYATA SARAAN DARIPADA PENGGAJIAN BAGI TAHUN " + str(year), S["title"]))
    el.append(Paragraph(
        "STATEMENT OF REMUNERATION FROM EMPLOYMENT FOR THE YEAR " + str(year), S["sub"]))
    el.append(Spacer(1, 6))

    # ── A. 雇主资料 ──
    el.append(_section_bar("A.  BUTIRAN MAJIKAN  /  PARTICULARS OF EMPLOYER", S, width))
    el.append(_kv_table([
        ("1", "Nama Majikan", "Employer's name", employer["name"]),
        ("2", "No. Cukai Majikan (No. E)", "Employer's no. (E)", employer["employer_no"]),
        ("3", "No. Pendaftaran SSM", "SSM registration no.", employer["ssm_no"]),
        ("4", "Alamat", "Address", employer["address"]),
    ], S, width))
    el.append(Spacer(1, 4))

    # ── B. 雇员资料 ──
    el.append(_section_bar("B.  BUTIRAN PEKERJA  /  PARTICULARS OF EMPLOYEE", S, width))
    el.append(_kv_table([
        ("1", "Nama Pekerja", "Employee's name", a["name"]),
        ("2", "No. Kad Pengenalan", "Identification card no.", a["ic_no"]),
        ("3", "No. KWSP (EPF)", "EPF no.", a["epf_no"]),
        ("4", "No. PERKESO (SOCSO)", "SOCSO no.", a["socso_no"]),
        ("5", "Jawatan", "Designation", a["designation"]),
        ("6", "Tempoh Penggajian", "Period of employment", f"01/01/{year} - 31/12/{year}"),
    ], S, width))
    el.append(Spacer(1, 4))

    # ── C. 薪酬收入 §13(1) ──
    salary = a["annual_gross"] - a["annual_bonus"] - a["annual_ot"]
    el.append(_section_bar(
        "C.  PENDAPATAN PENGGAJIAN — Perenggan 13(1)(a)  /  EMPLOYMENT INCOME — Para 13(1)(a)  (RM)", S, width))
    el.append(_kv_table([
        ("1(a)", "Gaji, upah, cuti, tuntutan",  "Salary, wages, leave pay", salary),
        ("1(b)", "Bonus / Gratuiti",            "Bonus / Gratuity", a["annual_bonus"]),
        ("1(c)", "Kerja lebih masa",            "Overtime", a["annual_ot"]),
        ("1(d)", "Yuran pengarah",              "Director's fee", 0),
        ("",     "JUMLAH SARAAN KASAR",         "TOTAL GROSS REMUNERATION", a["annual_gross"]),
    ], S, width, money_col=True))
    el.append(Spacer(1, 4))

    # ── D. 实物福利 / 住宿 ──
    el.append(_section_bar(
        "D.  MANFAAT BERUPA BARANGAN & TEMPAT KEDIAMAN — Perenggan 13(1)(b)(c)  /  BIK & VOLA  (RM)", S, width))
    el.append(_kv_table([
        ("1", "Manfaat berupa barangan (BIK)", "Benefits-in-kind", 0),
        ("2", "Nilai tempat kediaman (VOLA)",  "Value of living accommodation", 0),
    ], S, width, money_col=True))
    el.append(Spacer(1, 4))

    # ── E. 扣除项 / PCB ──
    el.append(_section_bar(
        "E.  POTONGAN & PCB  /  DEDUCTIONS & MONTHLY TAX DEDUCTION (MTD)  (RM)", S, width))
    el.append(_kv_table([
        ("1", "PCB / Potongan Cukai Bulanan", "MTD / Monthly tax deduction", a["annual_pcb"]),
        ("2", "Caruman KWSP (Pekerja)",       "EPF (Employee)", a["annual_epf_emp"]),
        ("3", "Caruman PERKESO",              "SOCSO", a["annual_socso_emp"]),
        ("4", "Caruman SIP (EIS)",            "EIS", a["annual_eis_emp"]),
        ("5", "Zakat / Fitrah",               "Zakat / Fitrah", a.get("annual_zakat", 0)),
    ], S, width, money_col=True))
    el.append(Spacer(1, 4))

    # ── F. 免税津贴 ──
    el.append(_section_bar(
        "F.  ELAUN / PERKUISIT / PEMBERIAN / MANFAAT DIKECUALIKAN CUKAI  /  TAX-EXEMPT ALLOWANCES  (RM)", S, width))
    el.append(_kv_table([
        ("1", "Elaun petrol / perjalanan (≤6,000)", "Petrol / travel allowance", min(a["annual_taxexempt"], 6000)),
        ("2", "Elaun penjagaan anak (≤2,400)",      "Childcare allowance", 0),
        ("3", "Makan / tempat letak kereta",        "Meal / parking", 0),
        ("4", "Anugerah perkhidmatan (≤2,000)",     "Long service award", 0),
    ], S, width, money_col=True))
    el.append(Spacer(1, 8))

    # ── 签署栏 ──
    sign = Table([
        [Paragraph("Tarikh / Date: ____________________", S["lbl"]),
         Paragraph("Tandatangan & Cop Majikan<br/>Signature & Employer's Stamp", S["lbl"])],
        ["", Paragraph("____________________________", S["lbl"])],
    ], colWidths=[width / 2, width / 2])
    sign.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    el.append(sign)
    el.append(Spacer(1, 4))
    el.append(HRFlowable(width="100%", thickness=0.4, color=LINE))
    el.append(Paragraph(
        "Borang ini hendaklah disediakan dan diserahkan kepada pekerja sebelum atau pada 28 Februari "
        f"{year + 1}.  /  This form must be rendered to the employee on or before 28 February {year + 1}.",
        S["foot"]))
    el.append(Paragraph(
        "Dijana oleh Paydaes ClaimGPT · Pengiraan PCB mengikut Kaedah Pengiraan Berkomputer LHDN. "
        "Sila sahkan dengan sistem rasmi HASiL sebelum pemfailan.", S["foot"]))
    return el


def build_ea_pdf(company: str = "my", year: int | None = None, emp_no: str = "") -> dict:
    """生成 EA Form (C.P.8A) 官方版式 PDF。emp_no 为空则全员(每人一页)。"""
    year = year or (datetime.now().year - 1)
    employer = pd.EMPLOYER
    S = _styles()

    emps = pd.PAYROLL_EMPLOYEES
    if emp_no:
        emps = [e for e in emps if e["emp_no"] == emp_no]
        if not emps:
            return {"error": f"找不到员工 {emp_no}"}

    fname = f"ea_form_official_{company}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, fname)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"Form EA (C.P.8A) {year}", author="Paydaes ClaimGPT",
    )
    width = A4[0] - 30 * mm
    from reportlab.platypus import PageBreak
    story = []
    for i, e in enumerate(emps):
        a = pd.compute_annual(e)
        story.extend(_emp_page(a, year, employer, S, width))
        if i < len(emps) - 1:
            story.append(PageBreak())

    doc.build(story)
    return {
        "ok": True,
        "filename": fname,
        "download_url": f"/api/report/download/{fname}",
        "size": os.path.getsize(path),
        "title": f"EA Form (C.P.8A) {year} · 官方PDF版",
        "pages": len(emps),
    }
