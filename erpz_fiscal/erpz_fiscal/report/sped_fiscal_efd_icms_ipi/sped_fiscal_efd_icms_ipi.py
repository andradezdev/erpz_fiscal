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
    gerar_k = cint_filter(filters.get("gerar_bloco_k", 1))
    bloco_filtro = filters.get("filtrar_bloco") or "Todos os Blocos"

    dt_ini_str = from_date.replace("-", "")[6:8] + from_date.replace("-", "")[4:6] + from_date.replace("-", "")[0:4]
    dt_fim_str = to_date.replace("-", "")[6:8] + to_date.replace("-", "")[4:6] + to_date.replace("-", "")[0:4]

    linhas_bloco_0 = []
    linhas_bloco_c = []
    linhas_bloco_e = []
    linhas_bloco_k = []
    linhas_bloco_9 = []

    comp = frappe.get_doc("Company", empresa) if frappe.db.exists("Company", empresa) else None
    cnpj_clean = (comp.tax_id or "18594769000140").replace(".", "").replace("-", "").replace("/", "") if comp else "18594769000140"

    # === BLOCO 0: Abertura e Identificação ===
    linhas_bloco_0.append(f"|0000|018|0|{dt_ini_str}|{dt_fim_str}|{empresa[:60]}|{cnpj_clean}||SP|123456789112|3550308|||A|1|")
    linhas_bloco_0.append("|0001|0|")
    linhas_bloco_0.append(f"|0005|{empresa[:35]}|01310100|AVENIDA PAULISTA|1500||BELA VISTA|1130001234||contato@erpz.io|")
    linhas_bloco_0.append(f"|0990|4|")

    # === BLOCO C: Documentos Fiscais (NF-e 55 / NFC-e 65) ===
    linhas_bloco_c.append("|C001|0|")
    dfes = frappe.get_all(
        "Documento Fiscal Eletronico",
        filters={"empresa": empresa, "status": "Autorizado"},
        fields=["name", "numero_nota", "serie", "data_autorizacao", "chave_acesso", "valor_total", "valor_icms", "modelo_fiscal"]
    )
    for d in dfes:
        data_str = d.data_autorizacao.strftime("%d%m%Y") if hasattr(d.data_autorizacao, "strftime") else dt_ini_str
        mod = "65" if "65" in (d.modelo_fiscal or "") else "55"
        v_tot = f"{flt(d.valor_total):.2f}".replace(".", ",")
        v_icms = f"{flt(d.valor_icms):.2f}".replace(".", ",")
        linhas_bloco_c.append(f"|C100|1|0||{mod}|00|{d.serie or 1}|{d.numero_nota}|{d.chave_acesso}|{data_str}|{data_str}|{v_tot}|0|0|0|{v_tot}|9|0|0|0|{v_tot}|0|0|{v_icms}|0|0|0|0|")

    linhas_bloco_c.append(f"|C990|{len(linhas_bloco_c) + 1}|")

    # === BLOCO E: Apuração do ICMS ===
    linhas_bloco_e.append("|E001|0|")
    linhas_bloco_e.append(f"|E100|{dt_ini_str}|{dt_fim_str}|")
    tot_debito = sum(flt(d.valor_icms) for d in dfes)
    deb_str = f"{tot_debito:.2f}".replace(".", ",")
    linhas_bloco_e.append(f"|E110|{deb_str}|0,00|0,00|0,00|0,00|0,00|0,00|{deb_str}|0,00|0,00|{deb_str}|0,00|0,00|0,00|")
    linhas_bloco_e.append(f"|E990|4|")

    # === BLOCO K: Controle da Produção e do Estoque (Integrado com ERPZ MRP) ===
    if gerar_k:
        linhas_bloco_k.append("|K001|0|")
        linhas_bloco_k.append(f"|K100|{dt_ini_str}|{dt_fim_str}|")

        # K200: Estoque Escriturado por Produto e Armazém
        estoques = frappe.db.sql("""
            SELECT b.item_code, SUM(b.actual_qty) as total_qty, i.item_group
            FROM `tabBin` b
            INNER JOIN `tabItem` i ON i.name = b.item_code
            WHERE i.disabled = 0 AND b.actual_qty > 0
            GROUP BY b.item_code
            LIMIT 50
        """, as_dict=True)

        for est in estoques:
            tipo_est = "04" if est.item_group == "Produtos Acabados" else ("03" if "Sub" in str(est.item_group) else "01")
            q_str = f"{flt(est.total_qty):.3f}".replace(".", ",")
            linhas_bloco_k.append(f"|K200|{dt_fim_str}|{est.item_code}|{q_str}|{tipo_est}||")

        # K230 / K235: Produção e Insumos Consumidos (Work Orders do MRP)
        work_orders = frappe.get_all(
            "Work Order",
            filters={"company": empresa, "status": ["in", ["Completed", "In Process"]]},
            fields=["name", "production_item", "qty", "produced_qty"],
            limit=30
        )

        for wo in work_orders:
            q_prod = flt(wo.produced_qty or wo.qty)
            q_p_str = f"{q_prod:.3f}".replace(".", ",")
            linhas_bloco_k.append(f"|K230|{dt_ini_str}|{dt_fim_str}|{wo.name}|{wo.production_item}|{q_p_str}||")

            # Consumo de insumos K235
            wo_items = frappe.get_all("Work Order Item", filters={"parent": wo.name}, fields=["item_code", "consumed_qty", "required_qty"], limit=5)
            for woi in wo_items:
                q_ins = flt(woi.consumed_qty or woi.required_qty)
                if q_ins > 0:
                    q_ins_str = f"{q_ins:.3f}".replace(".", ",")
                    linhas_bloco_k.append(f"|K235|{dt_ini_str}|{woi.item_code}|{q_ins_str}||")

        linhas_bloco_k.append(f"|K990|{len(linhas_bloco_k) + 1}|")
    else:
        linhas_bloco_k.append("|K001|1|") # 1 = Bloco sem dados
        linhas_bloco_k.append("|K990|2|")

    # === BLOCO 9: Encerramento e Totalizadores ===
    total_linhas_arquivo = len(linhas_bloco_0) + len(linhas_bloco_c) + len(linhas_bloco_e) + len(linhas_bloco_k) + 7
    linhas_bloco_9.append("|9001|0|")
    linhas_bloco_9.append("|9900|0000|1|")
    linhas_bloco_9.append(f"|9900|C100|{len(dfes)}|")
    linhas_bloco_9.append(f"|9900|K200|{len(estoques) if gerar_k else 0}|")
    linhas_bloco_9.append(f"|9990|5|")
    linhas_bloco_9.append(f"|9999|{total_linhas_arquivo}|")

    # Filtro visual para a tela
    if "Bloco K" in bloco_filtro:
        linhas_exibir = linhas_bloco_k
    elif "Bloco C" in bloco_filtro:
        linhas_exibir = linhas_bloco_c
    elif "Bloco E" in bloco_filtro:
        linhas_exibir = linhas_bloco_e
    elif "Bloco 0" in bloco_filtro:
        linhas_exibir = linhas_bloco_0
    elif "Bloco 9" in bloco_filtro:
        linhas_exibir = linhas_bloco_9
    else:
        linhas_exibir = linhas_bloco_0 + linhas_bloco_c + linhas_bloco_e + linhas_bloco_k + linhas_bloco_9

    return columns, [{"linha": l} for l in linhas_exibir]

def cint_filter(val):
    return 1 if str(val) in ("1", "true", "True") else 0
