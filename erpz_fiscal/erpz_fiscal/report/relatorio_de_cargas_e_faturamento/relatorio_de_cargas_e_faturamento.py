import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = [
        {"fieldname": "carga", "label": _("Nº Carga"), "fieldtype": "Link", "options": "Montagem de Carga", "width": 140},
        {"fieldname": "data_carga", "label": _("Data Carga"), "fieldtype": "Date", "width": 100},
        {"fieldname": "status_carga", "label": _("Status Carga"), "fieldtype": "Data", "width": 110},
        {"fieldname": "placa_veiculo", "label": _("Placa"), "fieldtype": "Data", "width": 90},
        {"fieldname": "sales_order", "label": _("Nº Pedido"), "fieldtype": "Link", "options": "Sales Order", "width": 130},
        {"fieldname": "customer_name", "label": _("Nome do Cliente"), "fieldtype": "Data", "width": 200},
        {"fieldname": "volumes", "label": _("Volumes"), "fieldtype": "Float", "width": 90},
        {"fieldname": "peso_liquido", "label": _("P. Líquido (kg)"), "fieldtype": "Float", "width": 110},
        {"fieldname": "peso_bruto", "label": _("P. Bruto (kg)"), "fieldtype": "Float", "width": 110},
        {"fieldname": "valor_pedido", "label": _("Valor Pedido"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "sales_invoice", "label": _("Fatura"), "fieldtype": "Link", "options": "Sales Invoice", "width": 130},
        {"fieldname": "numero_nfe", "label": _("Nº NF Autorizada"), "fieldtype": "Data", "width": 130},
        {"fieldname": "status_faturamento", "label": _("Status"), "fieldtype": "Data", "width": 110}
    ]

    conditions = []
    values = {}
    if filters.get("empresa"):
        conditions.append("c.empresa = %(empresa)s")
        values["empresa"] = filters.get("empresa")
    if filters.get("carga"):
        conditions.append("c.name = %(carga)s")
        values["carga"] = filters.get("carga")
    if filters.get("status_carga"):
        conditions.append("c.status = %(status_carga)s")
        values["status_carga"] = filters.get("status_carga")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT
            c.name as carga, c.data_carga, c.status as status_carga, c.placa_veiculo,
            i.sales_order, i.customer_name, i.volumes, i.peso_liquido, i.peso_bruto,
            i.valor_pedido, i.sales_invoice, i.numero_nfe, i.status_faturamento
        FROM `tabMontagem de Carga` c
        INNER JOIN `tabMontagem de Carga Item` i ON i.parent = c.name
        {where}
        ORDER BY c.data_carga DESC, c.name DESC
    """
    data = frappe.db.sql(query, values, as_dict=1)
    return columns, data
