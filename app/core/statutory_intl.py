"""
多国法定薪酬引擎 (International Statutory Payroll Engine)
═══════════════════════════════════════════════════════════════
为「AI 老板驾驶舱」提供 7 国各自的法定扣除/雇主缴纳计算,
让驾驶舱里每家公司的「企业总成本」由其本国真实法定结构驱动,而非统一 MY 公式。

支持国别(雇员扣除 EE / 雇主缴纳 ER):
  · 🇲🇾 MY  EPF(KWSP) + SOCSO(PERKESO) + EIS + PCB
  · 🇸🇬 SG  CPF(中央公积金, 按年龄分级 EE20%/ER17%, 上限) + SDL(技能发展税)
  · 🇨🇳 CN  五险一金(养老/医疗/失业/工伤/生育 + 住房公积金) + 个人所得税
  · 🇹🇭 TH  SSF(社会保障基金 5%, 月上限 750 THB) + PIT(个人所得税)
  · 🇭🇰 HK  MPF(强积金 5%, 月上限 1500 HKD) [HK 无强制个税预扣]
  · 🇻🇳 VN  SI/HI/UI(社保8%/医保1.5%/失业1%) + PIT
  · 🇮🇩 ID  BPJS(健康1%/养老1%/JHT2% 等) + PPh21

免责声明: 费率为各国通用近似值(2024 现行),用于演示与对比,正式申报以各国官方表为准。
统一返回结构:
  {
    "country", "currency",
    "gross",                 # 应税总收入
    "ee": {item: amount},    # 雇员各项扣除明细
    "er": {item: amount},    # 雇主各项缴纳明细
    "ee_total", "er_total",
    "income_tax",            # 个税(已含在 ee 中, 单列方便归因)
    "net_pay",               # 实发
    "employer_contrib",      # 雇主缴纳合计(= er_total)
    "total_cost",            # 企业总成本(= gross + er_total)
  }
"""
from __future__ import annotations


def _r(v: float) -> float:
    return round(float(v), 2)


# ════════════════════ 🇲🇾 马来西亚 ════════════════════
def _my(gross: float) -> dict:
    epf_ee = gross * 0.11
    epf_er = gross * (0.13 if gross <= 5000 else 0.12)
    socso_base = min(gross, 5000.0)
    socso_ee = socso_base * 0.005
    socso_er = socso_base * 0.0175
    eis_base = min(gross, 5000.0)
    eis_ee = eis_base * 0.002
    eis_er = eis_base * 0.002
    hrdf = gross * 0.01
    # 简化累进 PCB(月度): 起征 ~2900,逐级累进
    tax = _my_pcb(gross, epf_ee)
    ee = {"EPF": _r(epf_ee), "SOCSO": _r(socso_ee), "EIS": _r(eis_ee), "PCB": _r(tax)}
    er = {"EPF": _r(epf_er), "SOCSO": _r(socso_er), "EIS": _r(eis_er), "HRDF": _r(hrdf)}
    return _assemble("MY", "MYR", gross, ee, er, tax)


def _my_pcb(gross: float, epf_ee: float) -> float:
    annual = (gross - epf_ee) * 12 - 9000  # 个人宽免 9000
    if annual <= 5000:
        return 0.0
    # 马来西亚 2024 累进(简化)
    brackets = [(5000, 0.0), (15000, 0.01), (35000, 0.03), (50000, 0.06),
                (70000, 0.11), (100000, 0.19), (400000, 0.25)]
    tax, last = 0.0, 0
    for cap, rate in brackets:
        if annual > cap:
            tax += (cap - last) * rate; last = cap
        else:
            tax += (annual - last) * rate; break
    return _r(max(0.0, tax / 12))


# ════════════════════ 🇸🇬 新加坡 (CPF) ════════════════════
def _sg(gross: float) -> dict:
    # CPF 普通工资月上限 6800(2024),55 岁以下 EE 20% / ER 17%
    cpf_base = min(gross, 6800.0)
    cpf_ee = cpf_base * 0.20
    cpf_er = cpf_base * 0.17
    # SDL 技能发展税: 0.25%, 月上限 11.25
    sdl = min(gross * 0.0025, 11.25)
    tax = _sg_pit(gross, cpf_ee)
    ee = {"CPF": _r(cpf_ee), "Income Tax": _r(tax)}
    er = {"CPF": _r(cpf_er), "SDL": _r(sdl)}
    return _assemble("SG", "SGD", gross, ee, er, tax)


def _sg_pit(gross: float, cpf_ee: float) -> float:
    annual = (gross - cpf_ee) * 12 - 1000
    if annual <= 20000:
        return 0.0
    brackets = [(20000, 0.0), (30000, 0.02), (40000, 0.035), (80000, 0.07),
                (120000, 0.115), (160000, 0.15), (320000, 0.20)]
    tax, last = 0.0, 0
    for cap, rate in brackets:
        if annual > cap:
            tax += (cap - last) * rate; last = cap
        else:
            tax += (annual - last) * rate; break
    return _r(max(0.0, tax / 12))


# ════════════════════ 🇨🇳 中国 (五险一金) ════════════════════
def _cn(gross: float) -> dict:
    # 社保缴费基数(简化:不设上下限封顶,贴近一线白领量级)
    base = gross
    # 雇员: 养老8% 医疗2% 失业0.5% 公积金12%
    ee_pension = base * 0.08
    ee_medical = base * 0.02
    ee_unemploy = base * 0.005
    ee_housing = base * 0.12
    # 雇主: 养老16% 医疗9.5% 失业0.5% 工伤0.4% 生育1% 公积金12%
    er_pension = base * 0.16
    er_medical = base * 0.095
    er_unemploy = base * 0.005
    er_injury = base * 0.004
    er_maternity = base * 0.01
    er_housing = base * 0.12
    ee_social = ee_pension + ee_medical + ee_unemploy + ee_housing
    tax = _cn_iit(gross, ee_social)
    ee = {"养老": _r(ee_pension), "医疗": _r(ee_medical), "失业": _r(ee_unemploy),
          "公积金": _r(ee_housing), "个税": _r(tax)}
    er = {"养老": _r(er_pension), "医疗": _r(er_medical), "失业": _r(er_unemploy),
          "工伤": _r(er_injury), "生育": _r(er_maternity), "公积金": _r(er_housing)}
    return _assemble("CN", "CNY", gross, ee, er, tax)


def _cn_iit(gross: float, ee_social: float) -> float:
    # 中国个税: 月度预扣(简化为月度累进),起征 5000,先扣社保
    taxable = gross - ee_social - 5000
    if taxable <= 0:
        return 0.0
    brackets = [(3000, 0.03), (12000, 0.10), (25000, 0.20), (35000, 0.25),
                (55000, 0.30), (80000, 0.35), (float("inf"), 0.45)]
    deducts = [0, 210, 1410, 2660, 4410, 7160, 15160]
    last, rate, quick = 0, 0.03, 0
    for i, (cap, r) in enumerate(brackets):
        if taxable <= cap:
            rate, quick = r, deducts[i]; break
        rate, quick = r, deducts[i]
    return _r(max(0.0, taxable * rate - quick))


# ════════════════════ 🇹🇭 泰国 (SSF) ════════════════════
def _th(gross: float) -> dict:
    # SSF 社保: 5%, 计费上限 15000 THB → 月上限 750
    ssf_base = min(gross, 15000.0)
    ssf_ee = ssf_base * 0.05
    ssf_er = ssf_base * 0.05
    tax = _th_pit(gross, ssf_ee)
    ee = {"SSF": _r(ssf_ee), "PIT": _r(tax)}
    er = {"SSF": _r(ssf_er)}
    return _assemble("TH", "THB", gross, ee, er, tax)


def _th_pit(gross: float, ssf_ee: float) -> float:
    annual = (gross - ssf_ee) * 12 - 60000  # 个人免税额 60000
    if annual <= 150000:
        return 0.0
    brackets = [(150000, 0.0), (300000, 0.05), (500000, 0.10), (750000, 0.15),
                (1000000, 0.20), (2000000, 0.25), (5000000, 0.30)]
    tax, last = 0.0, 0
    for cap, rate in brackets:
        if annual > cap:
            tax += (cap - last) * rate; last = cap
        else:
            tax += (annual - last) * rate; break
    return _r(max(0.0, tax / 12))


# ════════════════════ 🇭🇰 香港 (MPF) ════════════════════
def _hk(gross: float) -> dict:
    # MPF 强积金: EE/ER 各 5%, 月上限 1500(月薪>30000封顶)
    mpf_ee = min(gross * 0.05, 1500.0)
    mpf_er = min(gross * 0.05, 1500.0)
    # 香港无强制个税月度预扣(年度薪俸税自评),驾驶舱按年度估算分摊以体现成本
    tax = _hk_salaries_tax(gross, mpf_ee)
    ee = {"MPF": _r(mpf_ee), "Salaries Tax(估)": _r(tax)}
    er = {"MPF": _r(mpf_er)}
    return _assemble("HK", "HKD", gross, ee, er, tax)


def _hk_salaries_tax(gross: float, mpf_ee: float) -> float:
    annual = (gross - mpf_ee) * 12 - 132000  # 基本免税额 132000
    if annual <= 0:
        return 0.0
    brackets = [(50000, 0.02), (50000, 0.06), (50000, 0.10), (50000, 0.14), (float("inf"), 0.17)]
    tax, rem = 0.0, annual
    for width, rate in brackets:
        take = min(rem, width)
        tax += take * rate; rem -= take
        if rem <= 0:
            break
    # 标准税率封顶 15%
    tax = min(tax, annual * 0.15)
    return _r(max(0.0, tax / 12))


# ════════════════════ 🇻🇳 越南 (SI/HI/UI) ════════════════════
def _vn(gross: float) -> dict:
    # 雇员: 社保8% 医保1.5% 失业1% = 10.5%
    si_ee = gross * 0.08
    hi_ee = gross * 0.015
    ui_ee = gross * 0.01
    # 雇主: 社保17.5% 医保3% 失业1% = 21.5%
    si_er = gross * 0.175
    hi_er = gross * 0.03
    ui_er = gross * 0.01
    ee_ins = si_ee + hi_ee + ui_ee
    tax = _vn_pit(gross, ee_ins)
    ee = {"社保": _r(si_ee), "医保": _r(hi_ee), "失业": _r(ui_ee), "PIT": _r(tax)}
    er = {"社保": _r(si_er), "医保": _r(hi_er), "失业": _r(ui_er)}
    return _assemble("VN", "VND", gross, ee, er, tax)


def _vn_pit(gross: float, ee_ins: float) -> float:
    # 越南个税: 月度累进,本人减除 1100万盾
    taxable = gross - ee_ins - 11000000
    if taxable <= 0:
        return 0.0
    brackets = [(5000000, 0.05), (10000000, 0.10), (18000000, 0.15), (32000000, 0.20),
                (52000000, 0.25), (80000000, 0.30), (float("inf"), 0.35)]
    tax, last = 0.0, 0
    for cap, rate in brackets:
        if taxable > cap:
            tax += (cap - last) * rate; last = cap
        else:
            tax += (taxable - last) * rate; break
    return _r(max(0.0, tax))


# ════════════════════ 🇮🇩 印尼 (BPJS + PPh21) ════════════════════
def _id(gross: float) -> dict:
    # 雇员: BPJS 健康1% + 养老JHT2% + 退休JP1%
    health_ee = gross * 0.01
    jht_ee = gross * 0.02
    jp_ee = gross * 0.01
    # 雇主: 健康4% + JHT3.7% + JP2% + 工伤0.24% + 死亡0.3%
    health_er = gross * 0.04
    jht_er = gross * 0.037
    jp_er = gross * 0.02
    jkk_er = gross * 0.0024
    jkm_er = gross * 0.003
    ee_bpjs = health_ee + jht_ee + jp_ee
    tax = _id_pph21(gross, ee_bpjs)
    ee = {"BPJS健康": _r(health_ee), "JHT养老": _r(jht_ee), "JP退休": _r(jp_ee), "PPh21": _r(tax)}
    er = {"BPJS健康": _r(health_er), "JHT养老": _r(jht_er), "JP退休": _r(jp_er),
          "工伤": _r(jkk_er), "死亡": _r(jkm_er)}
    return _assemble("ID", "IDR", gross, ee, er, tax)


def _id_pph21(gross: float, ee_bpjs: float) -> float:
    # PPh21: 年度累进,PTKP(免税)54,000,000
    annual = (gross - ee_bpjs) * 12 - 54000000
    if annual <= 0:
        return 0.0
    brackets = [(60000000, 0.05), (190000000, 0.15), (250000000, 0.25),
                (4750000000, 0.30), (float("inf"), 0.35)]
    tax, last = 0.0, 0
    for cap, rate in brackets:
        if annual > cap:
            tax += (cap - last) * rate; last = cap
        else:
            tax += (annual - last) * rate; break
    return _r(max(0.0, tax / 12))


# ════════════════════ 公共组装 ════════════════════
def _assemble(country: str, currency: str, gross: float, ee: dict, er: dict, tax: float) -> dict:
    ee_total = _r(sum(ee.values()))
    er_total = _r(sum(er.values()))
    net = _r(gross - ee_total)
    return {
        "country": country, "currency": currency,
        "gross": _r(gross),
        "ee": ee, "er": er,
        "ee_total": ee_total, "er_total": er_total,
        "income_tax": _r(tax),
        "net_pay": net,
        "employer_contrib": er_total,
        "total_cost": _r(gross + er_total),
    }


_DISPATCH = {
    "MY": _my, "SG": _sg, "CN": _cn, "TH": _th, "HK": _hk, "VN": _vn, "ID": _id,
}

# 各国法定体系简称(供前端/文案展示)
SCHEME_NAME = {
    "MY": {"zh": "EPF/SOCSO/EIS/PCB", "en": "EPF/SOCSO/EIS/PCB"},
    "SG": {"zh": "CPF 公积金 + SDL", "en": "CPF + SDL"},
    "CN": {"zh": "五险一金 + 个税", "en": "Social Insurance + Housing Fund + IIT"},
    "TH": {"zh": "SSF 社保 + 个税", "en": "SSF + PIT"},
    "HK": {"zh": "MPF 强积金 + 薪俸税", "en": "MPF + Salaries Tax"},
    "VN": {"zh": "社保/医保/失业 + 个税", "en": "SI/HI/UI + PIT"},
    "ID": {"zh": "BPJS + PPh21", "en": "BPJS + PPh21"},
}


def compute_statutory(country: str, gross: float) -> dict:
    """按国家计算法定扣除/雇主缴纳/企业总成本。
    country 不支持时回退 MY。"""
    fn = _DISPATCH.get(country, _my)
    return fn(float(gross or 0))


def employer_buckets(er: dict) -> dict:
    """把各国雇主缴纳明细归并到 4 个通用桶(供驾驶舱 KPI/归因 与 发薪汇总 共用,
    避免 analytics 与 payroll_batch 各写一份归并逻辑)。
      养老金/公积金类 → epf_er;医疗/社保类 → socso_er;
      失业/技能税 → eis_er;其余(工伤/生育/死亡/HRDF…) → hrdf
    返回 {epf_er, socso_er, eis_er, hrdf}(均已四舍五入)。"""
    epf_er = socso_er = eis_er = hrdf = 0.0
    for k, v in (er or {}).items():
        kl = k.lower()
        if any(t in k for t in ("养老", "JHT", "JP", "公积金")) or kl in ("cpf", "epf", "mpf"):
            epf_er += v
        elif any(t in k for t in ("医疗", "医保", "社保")) or kl in ("socso", "ssf", "si", "hi"):
            socso_er += v
        elif any(t in k for t in ("失业",)) or kl in ("eis", "sdl", "ui"):
            eis_er += v
        else:
            hrdf += v
    return {"epf_er": round(epf_er, 2), "socso_er": round(socso_er, 2),
            "eis_er": round(eis_er, 2), "hrdf": round(hrdf, 2)}
