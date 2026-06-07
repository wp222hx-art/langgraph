"""
报表导出 —— 真生成 Excel(.xlsx) / PPT(.pptx) 文件
数据来源:真实数据库(报销单 + 统计 + 余额调整流水)。
"""
from __future__ import annotations

import os
from datetime import datetime

from app.data import db, enterprise

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

REPORT_TITLES = {
    "rpt_claim": ("报销申请报表", "Claim Report"),
    "rpt_travel": ("差旅申请报表", "Travel Report"),
    "rpt_benefit": ("福利使用报表", "Benefits Usage Report"),
}


def _company_name(company: str) -> str:
    for g in enterprise.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                return c["name"]
    return company


def _gather(company: str):
    claims = db.list_claims(company, limit=500)
    stats = db.claim_stats(company)
    return claims, stats


def export_report(module_id: str, company: str, fmt: str = "excel") -> dict:
    title = REPORT_TITLES.get(module_id, (module_id, module_id))[0]
    cname = _company_name(company)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "ppt":
        fname = f"{module_id}_{company}_{ts}.pptx"
        path = os.path.join(EXPORT_DIR, fname)
        _build_ppt(path, title, cname, company)
    else:
        fmt = "excel"
        fname = f"{module_id}_{company}_{ts}.xlsx"
        path = os.path.join(EXPORT_DIR, fname)
        _build_xlsx(path, title, cname, company)
    return {"fmt": fmt, "filename": fname,
            "download_url": f"/api/report/download/{fname}",
            "size": os.path.getsize(path)}


def _build_xlsx(path: str, title: str, cname: str, company: str):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    claims, stats = _gather(company)
    wb = Workbook()
    ws = wb.active
    ws.title = "报销明细"

    head_fill = PatternFill("solid", fgColor="20C997")
    head_font = Font(bold=True, color="FFFFFF")

    ws.merge_cells("A1:H1")
    ws["A1"] = f"{cname} · {title}"
    ws["A1"].font = Font(bold=True, size=15, color="0F766E")
    ws["A2"] = f"生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["A3"] = (f"合计 {stats.get('pending',0)+stats.get('approved',0)+stats.get('rejected',0)+stats.get('paid',0)} 笔 · "
                f"待审 {stats.get('pending',0)} · 已批 {stats.get('approved',0)} · "
                f"已驳 {stats.get('rejected',0)} · 总额 {stats.get('total_amt',0)}")

    headers = ["单号", "申请人", "类型", "商户", "金额", "币种", "风险分", "状态"]
    r0 = 5
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=r0, column=ci, value=h)
        c.fill = head_fill; c.font = head_font
        c.alignment = Alignment(horizontal="center")
    st_map = {"pending": "待审批", "approved": "已批准", "rejected": "已驳回", "paid": "已支付"}
    for ri, cl in enumerate(claims, r0 + 1):
        row = [cl.get("id"), cl.get("emp_name"), cl.get("type_name"), cl.get("merchant"),
               cl.get("amount"), cl.get("currency"), cl.get("risk_score"),
               st_map.get(cl.get("status"), cl.get("status"))]
        for ci, v in enumerate(row, 1):
            ws.cell(row=ri, column=ci, value=v)
    widths = [18, 12, 12, 16, 10, 8, 8, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    # 第二张表:状态汇总
    ws2 = wb.create_sheet("状态汇总")
    ws2["A1"] = "状态"; ws2["B1"] = "笔数"
    ws2["A1"].font = head_font; ws2["B1"].font = head_font
    ws2["A1"].fill = head_fill; ws2["B1"].fill = head_fill
    for i, (k, label) in enumerate(st_map.items(), 2):
        ws2.cell(row=i, column=1, value=label)
        ws2.cell(row=i, column=2, value=stats.get(k, 0))
    wb.save(path)


def _build_ppt(path: str, title: str, cname: str, company: str):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor

    claims, stats = _gather(company)
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    TEAL = RGBColor(0x20, 0xC9, 0x97)

    # 封面
    s = prs.slides.add_slide(prs.slide_layouts[6])
    box = s.shapes.add_textbox(Inches(1), Inches(2.4), Inches(11), Inches(2))
    tf = box.text_frame
    tf.text = f"{cname}"
    tf.paragraphs[0].font.size = Pt(28); tf.paragraphs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    p = tf.add_paragraph(); p.text = title
    p.font.size = Pt(40); p.font.bold = True; p.font.color.rgb = TEAL
    p2 = tf.add_paragraph(); p2.text = f"Paydaes ClaimGPT · {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    p2.font.size = Pt(14); p2.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    # KPI 页
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    t2 = s2.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12), Inches(1))
    t2.text_frame.text = "关键指标 KPI"
    t2.text_frame.paragraphs[0].font.size = Pt(28); t2.text_frame.paragraphs[0].font.bold = True
    t2.text_frame.paragraphs[0].font.color.rgb = TEAL
    total = sum(stats.get(k, 0) for k in ("pending", "approved", "rejected", "paid"))
    kpis = [("报销总笔数", total), ("待审批", stats.get("pending", 0)),
            ("已批准", stats.get("approved", 0)), ("总金额", stats.get("total_amt", 0))]
    for i, (label, val) in enumerate(kpis):
        bx = s2.shapes.add_textbox(Inches(0.7 + i * 3.1), Inches(2.2), Inches(2.9), Inches(2))
        bf = bx.text_frame
        bf.text = str(val)
        bf.paragraphs[0].font.size = Pt(36); bf.paragraphs[0].font.bold = True; bf.paragraphs[0].font.color.rgb = TEAL
        pp = bf.add_paragraph(); pp.text = label
        pp.font.size = Pt(14); pp.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # 明细表页(前 12 行)
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    t3 = s3.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12), Inches(0.8))
    t3.text_frame.text = "报销明细(Top 12)"
    t3.text_frame.paragraphs[0].font.size = Pt(24); t3.text_frame.paragraphs[0].font.bold = True
    t3.text_frame.paragraphs[0].font.color.rgb = TEAL
    rows = min(len(claims), 12) + 1
    cols = 5
    tbl = s3.shapes.add_table(rows, cols, Inches(0.7), Inches(1.4), Inches(12), Inches(5)).table
    for ci, h in enumerate(["单号", "申请人", "类型", "金额", "状态"]):
        tbl.cell(0, ci).text = h
    st_map = {"pending": "待审", "approved": "已批", "rejected": "已驳", "paid": "已付"}
    for ri, cl in enumerate(claims[:12], 1):
        vals = [cl.get("id", ""), cl.get("emp_name", ""), cl.get("type_name", ""),
                f"{cl.get('amount','')} {cl.get('currency','')}", st_map.get(cl.get("status"), "")]
        for ci, v in enumerate(vals):
            tbl.cell(ri, ci).text = str(v)
    prs.save(path)
