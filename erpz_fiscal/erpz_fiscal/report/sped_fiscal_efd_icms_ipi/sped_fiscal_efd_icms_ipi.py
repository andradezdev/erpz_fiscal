import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"fieldname": "linha", "label": _("Registro SPED Fiscal (Linha Formatada EFD ICMS/IPI)"), "fieldtype": "Data", "width": 800}
    ]

    empresa = filters.get("empresa") or frappe.db.get_single_value("Global Defaults", "default_company")
    from_date = str(filters.get("from_date") or "2026-09-01")
    to_date = str(filters.get("to_date") or "2026-09-30")

    dt_ini_str = from_date.replace("-", "")[6:8] + from_date.replace("-", "")[4:6] + from_date.replace("-", "")[0:4]
    dt_fim_str = to_date.replace("-", "")[6:8] + to_date.replace("-", "")[4:6] + to_date.replace("-", "")[0:4]

    linhas = []

    # === BLOCO 0: Abertura e Identificação ===
    comp = frappe.get_doc("Company", empresa) if frappe.db.exists("Company", empresa) else None
    cnpj_clean = (comp.tax_id or "18594769000140").replace(".", "").replace("-", "").replace("/", "") if comp else "18594769000140"
    
    linhas.append(f"|0000|018|0|{dt_ini_str}|{dt_fim_str}|{empresa[:60]}|{cnpj_clean}||SP|123456789112|3550308|||A|1|")
    linhas.append("|0001|0|")
    linhas.append(f"|0005|{empresa[:35]}|01310100|AVENIDA PAULISTA|1500||BELA VISTA|1130001234||contato@erpz.io|")
    linhas.append(f"|0990|{len(linhas) + 1}|")

    # === BLOCO C: Documentos Fiscais (NF-e 55 / NFC-e 65) ===
    bloco_c_start = len(linhas)
    linhas.append("|C001|0|")
    
    dfes = frappe.get_all(
        "Documento Fiscal Eletronico",
        filters={"empresa": empresa, "status": "Autorizado"},
        fields=["name", "numero_nota", "serie", "data_autorizacao", "chave_acesso", "valor_total", "valor_icms", "valor_produtos", "destinatario_nome", "modelo_fiscal"]
    )

    for d in dfes:
        data_str = d.data_autorizacao.strftime("%d%m%Y") if hasattr(d.data_autorizacao, "strftime") else dt_ini_str
        mod = "65" if "65" in (d.modelo_fiscal or "") else "55"
        v_tot = f"{flt(d.valor_total):.2f}".replace(".", ",")
        v_icms = f"{flt(d.valor_icms):.2f}".replace(".", ",")
        
        linhas.append(f"|C100|1|0||{mod}|00|{d.serie or 1}|{d.numero_nota}|{d.chave_acesso}|{data_str}|{data_str}|{v_tot}|0|0|0|{v_tot}|9|0|0|0|{v_tot}|0|0|{v_icms}|0|0|0|0|")

    linhas.append(f"|C990|{len(linhas) - bloco_c_start + 1}|")

    # === BLOCO E: Apuração do ICMS ===
    bloco_e_start = len(linhas)
    linhas.append("|E001|0|")
    linhas.append(f"|E100|{dt_ini_str}|{dt_fim_str}|")
    tot_debito = sum(flt(d.valor_icms) for d in dfes)
    deb_str = f"{tot_debito:.2f}".replace(".", ",")
    linhas.append(f"|E110|{deb_str}|0,00|0,00|0,00|0,00|0,00|0,00|{deb_str}|0,00|0,00|{deb_str}|0,00|0,00|0,00|")
    linhas.append(f"|E990|{len(linhas) - bloco_e_start + 1}|")

    # === BLOCO K: Controle da Produção e do Estoque (Integrado ao ERPZ MRP) ===
    bloco_k_start = len(linhas)
    linhas.append("|K001|0|")
    linhas.append(f"|K100|{dt_ini_str}|{dt_fim_str}|")

    # Registro K200: Estoque Escriturado por Produto
    estoques = frappe.db.sql("""
        SELECT b.item_code, SUM(b.actual_qty) as total_qty, i.stock_uom, i.item_group
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE i.disabled = 0 AND b.actual_qty > 0
        GROUP BY b.item_code
        LIMIT 50
    """, as_dict=True)

    for est in estoques:
        tipo_est = "04" if est.item_group == "Produtos Acabados" else ("03" if "Sub" in str(est.item_group) else "01")
        q_str = f"{flt(est.total_qty):.3f}".replace(".", ",")
        linhas.append(f"|K200|{dt_fim_str}|{est.item_code}|{q_str}|{tipo_est}||")

    # Registro K230 / K235: Produção do Período (Work Orders / MRP)
    work_orders = frappe.get_all(
        "Work Order",
        filters={"company": empresa, "status": ["in", ["Completed", "In Process"]]},
        fields=["name", "production_item", "qty", "produced_qty", "planned_start_date", "actual_end_date"],
        limit=25
    )

    for wo in work_orders:
        q_prod = flt(wo.produced_qty or wo.qty)
        q_p_str = f"{q_prod:.3f}".replace(".", ",")
        linhas.append(f"|K230|{dt_ini_str}|{dt_fim_str}|{wo.name}|{wo.production_item}|{q_p_str}||")

    linhas.append(f"|K990|{len(linhas) - bloco_k_start + 1}|")

    # === BLOCO 9: Encerramento do Arquivo Digital ===
    bloco_9_start = len(linhas)
    linhas.append("|9001|0|")
    linhas.append(f"|9900|0000|1|")
    linhas.append(f"|9900|C100|{len(dfes)}|")
    linhas.append(f"|9900|K200|{len(estoques)}|")
    linhas.append(f"|9900|K230|{len(work_orders)}|")
    linhas.append(f"|9990|{len(linhas) - bloco_9_start + 2}|")
    linhas.append(f"|9999|{len(linhas) + 1}|")

    data = [{"linha": l} for l in linhas]
    return columns, data
