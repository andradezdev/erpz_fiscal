import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname": "linha", "label": _("Registro SPED (Linha Formatada)"), "fieldtype": "Data", "width": 800}
    ]

    empresa = filters.get("empresa")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Gera registros b?sicos padrão SPED EFD
    linhas = [
        "|0000|018|0|{}|{}|{}|||||||||||".format(
            from_date.replace("-", ""), to_date.replace("-", ""), empresa[:60]
        ),
        "|0001|0|",
        "|0990|3|"
    ]

    # Busca Documentos Fiscais no per?odo
    dfes = frappe.get_all(
        "Documento Fiscal Eletronico",
        filters={"empresa": empresa, "status": "Autorizado"},
        fields=["name", "numero_nota", "serie", "data_autorizacao", "chave_acesso", "valor_total", "valor_icms"]
    )

    for d in dfes:
        data_str = (d.data_autorizacao or "").strftime("%d%m%Y") if hasattr(d.data_autorizacao, "strftime") else "01012026"
        linhas.append(f"|C100|1|0||55|00|{d.serie}|{d.numero_nota}|{d.chave_acesso}|{data_str}|{data_str}|{d.valor_total}|0|0|0|{d.valor_total}|9|0|0|0|{d.valor_total}|0|0|{d.valor_icms}|0|0|0|0|")

    linhas.append(f"|C990|{len(dfes) + 2}|")
    linhas.append("|9001|0|")
    linhas.append(f"|9999|{len(linhas) + 2}|")

    data = [{"linha": l} for l in linhas]
    return columns, data
