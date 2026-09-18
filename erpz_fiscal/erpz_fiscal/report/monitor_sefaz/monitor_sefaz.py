import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"fieldname": "numero_nota", "label": _("Nº"), "fieldtype": "Int", "width": 75, "align": "center"},
        {"fieldname": "serie", "label": _("Série"), "fieldtype": "Int", "width": 65, "align": "center"},
        {"fieldname": "modelo_fiscal", "label": _("Modelo"), "fieldtype": "Data", "width": 90, "align": "center"},
        {"fieldname": "name", "label": _("Documento"), "fieldtype": "Link", "options": "Documento Fiscal Eletronico", "width": 155},
        {"fieldname": "data_emissao", "label": _("Data Emissão"), "fieldtype": "Datetime", "width": 155, "align": "center"},
        {"fieldname": "destinatario_nome", "label": _("Destinatário"), "fieldtype": "Data", "width": 240},
        {"fieldname": "codigo_status_sefaz", "label": _("Status SEFAZ"), "fieldtype": "Data", "width": 165, "align": "center"},
        {"fieldname": "mensagem_sefaz", "label": _("Motivo SEFAZ (xMotivo)"), "fieldtype": "Data", "width": 300},
        {"fieldname": "valor_total", "label": _("Total (R$)"), "fieldtype": "Currency", "width": 120, "align": "right"},
        {"fieldname": "valor_ibs", "label": _("IBS (R$)"), "fieldtype": "Currency", "width": 105, "align": "right"},
        {"fieldname": "valor_cbs", "label": _("CBS (R$)"), "fieldtype": "Currency", "width": 105, "align": "right"},
        {"fieldname": "protocolo", "label": _("Protocolo"), "fieldtype": "Data", "width": 155, "align": "center"},
        {"fieldname": "chave_acesso", "label": _("Chave de Acesso"), "fieldtype": "Data", "width": 340}
    ]

    conditions = []
    values = {}

    if filters.get("empresa"):
        conditions.append("empresa = %(empresa)s")
        values["empresa"] = filters.get("empresa")

    if filters.get("modelo"):
        conditions.append("modelo_fiscal = %(modelo)s")
        values["modelo"] = filters.get("modelo")

    if filters.get("from_date"):
        conditions.append("DATE(data_emissao) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(data_emissao) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("status_filtro"):
        st = filters.get("status_filtro")
        if "100" in st:
            conditions.append("codigo_status_sefaz = '100'")
        elif "Rejeitadas" in st:
            conditions.append("(status = 'Rejeitado' OR (codigo_status_sefaz IS NOT NULL AND codigo_status_sefaz NOT IN ('100', '105', '101')))")
        elif "105" in st:
            conditions.append("codigo_status_sefaz = '105'")
        elif "Canceladas" in st:
            conditions.append("(status = 'Cancelado' OR codigo_status_sefaz = '101')")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    data = frappe.db.sql(f"""
        SELECT
            numero_nota, serie, modelo_fiscal, name, data_emissao, destinatario_nome,
            codigo_status_sefaz, mensagem_sefaz, valor_total, valor_ibs, valor_cbs,
            protocolo, chave_acesso, status
        FROM `tabDocumento Fiscal Eletronico`
        {where}
        ORDER BY creation DESC
    """, values, as_dict=1)

    # Chart
    tot_aut = len([r for r in data if r.get("codigo_status_sefaz") == "100" or r.get("status") == "Autorizado"])
    tot_rej = len([r for r in data if r.get("status") == "Rejeitado" or (r.get("codigo_status_sefaz") and r.get("codigo_status_sefaz") not in ("100", "105", "101"))])
    tot_pend = len(data) - tot_aut - tot_rej

    chart = {
        "data": {
            "labels": [_("Autorizadas"), _("Rejeitadas"), _("Pendentes / Processando")],
            "datasets": [{"values": [tot_aut, tot_rej, tot_pend]}]
        },
        "type": "donut",
        "colors": ["#16a34a", "#dc2626", "#ea580c"]
    }

    # Summary
    summary = [
        {"value": len(data), "label": _("Total Documentos"), "datatype": "Int"},
        {"value": tot_aut, "label": _("Autorizadas (100)"), "datatype": "Int", "indicator": "green"},
        {"value": tot_rej, "label": _("Rejeitadas com Erro"), "datatype": "Int", "indicator": "red"},
        {"value": sum(flt(r.get("valor_ibs", 0)) for r in data), "label": _("Total IBS (Reforma)"), "datatype": "Currency"},
        {"value": sum(flt(r.get("valor_cbs", 0)) for r in data), "label": _("Total CBS (Reforma)"), "datatype": "Currency"}
    ]

    return columns, data, None, chart, summary
