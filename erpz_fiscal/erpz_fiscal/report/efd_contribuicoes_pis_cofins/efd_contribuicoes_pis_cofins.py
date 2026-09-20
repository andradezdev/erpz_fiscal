import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"fieldname": "linha", "label": _("Registro EFD Contribuições (PIS/COFINS)"), "fieldtype": "Data", "width": 800}
    ]

    empresa = filters.get("empresa") or frappe.db.get_single_value("Global Defaults", "default_company")
    from_date = str(filters.get("from_date") or "2026-09-01")
    to_date = str(filters.get("to_date") or "2026-09-30")

    dt_ini_str = from_date.replace("-", "")[6:8] + from_date.replace("-", "")[4:6] + from_date.replace("-", "")[0:4]
    dt_fim_str = to_date.replace("-", "")[6:8] + to_date.replace("-", "")[4:6] + to_date.replace("-", "")[0:4]

    linhas = []

    comp = frappe.get_doc("Company", empresa) if frappe.db.exists("Company", empresa) else None
    cnpj_clean = (comp.tax_id or "18594769000140").replace(".", "").replace("-", "").replace("/", "") if comp else "18594769000140"

    # === BLOCO 0: Abertura ===
    linhas.append(f"|0000|006|0|{dt_ini_str}|{dt_fim_str}|{empresa[:60]}|{cnpj_clean}|SP|3550308||||")
    linhas.append("|0001|0|")
    linhas.append("|0110|1|1|||")
    linhas.append(f"|0140|0001|{empresa[:60]}|{cnpj_clean}|SP||3550308|||||")
    linhas.append(f"|0990|5|")

    # === BLOCO C: Documentos de Mercadorias ===
    bloco_c_start = len(linhas)
    linhas.append("|C001|0|")
    linhas.append(f"|C010|{cnpj_clean}|1|")

    dfes = frappe.get_all(
        "Documento Fiscal Eletronico",
        filters={"empresa": empresa, "status": "Autorizado"},
        fields=["name", "numero_nota", "serie", "data_autorizacao", "chave_acesso", "valor_total", "valor_pis", "valor_cofins"]
    )

    tot_pis = 0.0
    tot_cofins = 0.0

    for d in dfes:
        data_str = d.data_autorizacao.strftime("%d%m%Y") if hasattr(d.data_autorizacao, "strftime") else dt_ini_str
        v_tot = f"{flt(d.valor_total):.2f}".replace(".", ",")
        v_p = f"{flt(d.valor_pis):.2f}".replace(".", ",")
        v_c = f"{flt(d.valor_cofins):.2f}".replace(".", ",")
        tot_pis += flt(d.valor_pis)
        tot_cofins += flt(d.valor_cofins)

        linhas.append(f"|C100|1|0||55|00|{d.serie or 1}|{d.numero_nota}|{d.chave_acesso}|{data_str}|{data_str}|{v_tot}|0|0|0|{v_tot}|9|0|0|0|{v_tot}|0|0|0|{v_p}|{v_c}|0|0|")

    linhas.append(f"|C990|{len(linhas) - bloco_c_start + 1}|")

    # === BLOCO M: Apuração da Contribuição (M200 - PIS e M600 - COFINS) ===
    bloco_m_start = len(linhas)
    linhas.append("|M001|0|")
    p_str = f"{tot_pis:.2f}".replace(".", ",")
    c_str = f"{tot_cofins:.2f}".replace(".", ",")
    linhas.append(f"|M200|{p_str}|0,00|0,00|0,00|0,00|{p_str}|0,00|0,00|0,00|{p_str}|")
    linhas.append(f"|M600|{c_str}|0,00|0,00|0,00|0,00|{c_str}|0,00|0,00|0,00|{c_str}|")
    linhas.append(f"|M990|{len(linhas) - bloco_m_start + 1}|")

    # === BLOCO 9: Encerramento ===
    bloco_9_start = len(linhas)
    linhas.append("|9001|0|")
    linhas.append(f"|9900|0000|1|")
    linhas.append(f"|9900|C100|{len(dfes)}|")
    linhas.append(f"|9900|M200|1|")
    linhas.append(f"|9900|M600|1|")
    linhas.append(f"|9990|{len(linhas) - bloco_9_start + 2}|")
    linhas.append(f"|9999|{len(linhas) + 1}|")

    data = [{"linha": l} for l in linhas]
    return columns, data
