import frappe

def setup_desktop_and_sidebar():
    icon_name = frappe.db.get_value("Desktop Icon", {"link_to": "ERPZ Fiscal"}, "name")
    if not icon_name:
        icon_name = frappe.db.get_value("Desktop Icon", {"label": "ERPZ Fiscal"}, "name")
        
    if icon_name:
        frappe.db.set_value("Desktop Icon", icon_name, {
            "label": "ERPZ Fiscal",
            "icon": "file-text",
            "icon_type": "Link",
            "link_type": "Workspace Sidebar",
            "link_to": "ERPZ Fiscal",
            "hidden": 0,
            "standard": 1,
            "app": "erpz_fiscal",
            "idx": 8
        })
    else:
        new_icon = frappe.new_doc("Desktop Icon")
        new_icon.name = "ERPZ Fiscal"
        new_icon.label = "ERPZ Fiscal"
        new_icon.icon = "file-text"
        new_icon.icon_type = "Link"
        new_icon.link_type = "Workspace Sidebar"
        new_icon.link_to = "ERPZ Fiscal"
        new_icon.hidden = 0
        new_icon.standard = 1
        new_icon.app = "erpz_fiscal"
        new_icon.idx = 8
        new_icon.insert(ignore_permissions=True)

def after_install():
    create_roles()
    create_custom_fields()
    setup_desktop_and_sidebar()
    frappe.db.commit()

def after_migrate():
    create_custom_fields()
    setup_desktop_and_sidebar()
    frappe.db.commit()

def create_roles():
    roles = [
        {"role_name": "Fiscal Manager", "desk_access": 1, "is_custom": 1},
        {"role_name": "Fiscal User", "desk_access": 1, "is_custom": 1}
    ]
    for r in roles:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(r)
            doc.insert(ignore_permissions=True)

def create_custom_fields():
    fields = get_custom_fields()
    for doctype, field_list in fields.items():
        for f in field_list:
            fname = f"{doctype}-{f['fieldname']}"
            if not frappe.db.exists("Custom Field", fname):
                cf = frappe.new_doc("Custom Field")
                cf.dt = doctype
                cf.module = "ERPZ Fiscal"
                cf.update(f)
                cf.insert(ignore_permissions=True)

def get_custom_fields():
    return {
        "Item": [
            {
                "fieldname": "erpz_fiscal_section",
                "label": "Dados Fiscais Brasil",
                "fieldtype": "Section Break",
                "insert_after": "item_group",
                "collapsible": 1
            },
            {
                "fieldname": "ncm",
                "label": "NCM",
                "fieldtype": "Data",
                "insert_after": "erpz_fiscal_section",
                "description": "Nomenclatura Comum do Mercosul (8 dígitos)"
            },
            {
                "fieldname": "cest",
                "label": "CEST",
                "fieldtype": "Data",
                "insert_after": "ncm",
                "description": "Código Especificador da Substituição Tributária"
            },
            {
                "fieldname": "origem_fiscal",
                "label": "Origem da Mercadoria",
                "fieldtype": "Select",
                "options": "0 - Nacional\n1 - Estrangeira - Importação direta\n2 - Estrangeira - Adquirida no mercado interno",
                "default": "0 - Nacional",
                "insert_after": "cest"
            },
            {
                "fieldname": "column_break_pesos_item",
                "fieldtype": "Column Break",
                "insert_after": "origem_fiscal"
            },
            {
                "fieldname": "peso_liquido",
                "label": "Peso Líquido (kg)",
                "fieldtype": "Float",
                "precision": "3",
                "description": "Peso líquido unitário em kg",
                "insert_after": "column_break_pesos_item"
            },
            {
                "fieldname": "peso_bruto",
                "label": "Peso Bruto (kg)",
                "fieldtype": "Float",
                "precision": "3",
                "description": "Peso bruto unitário em kg",
                "insert_after": "peso_liquido"
            }
        ],
        "Sales Order": [
            {
                "fieldname": "erpz_fiscal_section_so",
                "label": "Dados Fiscais NF-e",
                "fieldtype": "Section Break",
                "insert_after": "terms",
                "collapsible": 1
            },
            {
                "fieldname": "documento_fiscal",
                "label": "Documento Fiscal Eletrônico",
                "fieldtype": "Link",
                "options": "Documento Fiscal Eletronico",
                "read_only": 1,
                "insert_after": "erpz_fiscal_section_so"
            },
            {
                "fieldname": "numero_nfe",
                "label": "Número NF-e",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "documento_fiscal"
            },
            {
                "fieldname": "chave_nfe",
                "label": "Chave NF-e",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "numero_nfe"
            },
            {
                "fieldname": "status_fiscal",
                "label": "Status Fiscal",
                "fieldtype": "Select",
                "options": "\nSem NF\nPendente\nAutorizada\nCancelada",
                "default": "Sem NF",
                "read_only": 1,
                "insert_after": "chave_nfe"
            }
        ],
        "POS Invoice": [
            {
                "fieldname": "erpz_fiscal_nfe_section",
                "label": "Nota Fiscal de Consumidor (NFC-e)",
                "fieldtype": "Section Break",
                "insert_after": "amended_from",
                "collapsible": 1
            },
            {
                "fieldname": "documento_fiscal",
                "label": "Documento Fiscal Eletrônico",
                "fieldtype": "Link",
                "options": "Documento Fiscal Eletronico",
                "read_only": 1,
                "insert_after": "erpz_fiscal_nfe_section"
            },
            {
                "fieldname": "chave_nfe",
                "label": "Chave NFC-e",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "documento_fiscal"
            },
            {
                "fieldname": "status_fiscal",
                "label": "Status Fiscal",
                "fieldtype": "Select",
                "options": "\nSem NF\nPendente\nAutorizada\nCancelada\nRejeitada",
                "default": "Sem NF",
                "read_only": 1,
                "insert_after": "chave_nfe"
            },
            {
                "fieldname": "column_break_fiscal_pos",
                "fieldtype": "Column Break",
                "insert_after": "status_fiscal"
            },
            {
                "fieldname": "numero_nfe",
                "label": "Número NFC-e",
                "fieldtype": "Int",
                "read_only": 1,
                "insert_after": "column_break_fiscal_pos"
            },
            {
                "fieldname": "serie_nfe",
                "label": "Série NFC-e",
                "fieldtype": "Int",
                "read_only": 1,
                "insert_after": "numero_nfe"
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "erpz_fiscal_nfe_section",
                "label": "Nota Fiscal Eletrônica",
                "fieldtype": "Section Break",
                "insert_after": "amended_from",
                "collapsible": 1
            },
            {
                "fieldname": "documento_fiscal",
                "label": "Documento Fiscal Eletrônico",
                "fieldtype": "Link",
                "options": "Documento Fiscal Eletronico",
                "read_only": 1,
                "insert_after": "erpz_fiscal_nfe_section"
            },
            {
                "fieldname": "chave_nfe",
                "label": "Chave NFe",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "documento_fiscal"
            },
            {
                "fieldname": "status_fiscal",
                "label": "Status Fiscal",
                "fieldtype": "Select",
                "options": "\nSem NF\nPendente\nAutorizada\nCancelada\nRejeitada",
                "default": "Sem NF",
                "read_only": 1,
                "insert_after": "chave_nfe"
            },
            {
                "fieldname": "column_break_fiscal_inv",
                "fieldtype": "Column Break",
                "insert_after": "status_fiscal"
            },
            {
                "fieldname": "numero_nfe",
                "label": "Número NFe",
                "fieldtype": "Int",
                "read_only": 1,
                "insert_after": "column_break_fiscal_inv"
            },
            {
                "fieldname": "serie_nfe",
                "label": "Série NFe",
                "fieldtype": "Int",
                "read_only": 1,
                "insert_after": "numero_nfe"
            },
            {
                "fieldname": "volumes",
                "label": "Volumes",
                "fieldtype": "Float",
                "default": "1",
                "insert_after": "serie_nfe"
            },
            {
                "fieldname": "peso_liquido",
                "label": "Peso Líquido Total (kg)",
                "fieldtype": "Float",
                "precision": "3",
                "insert_after": "volumes"
            },
            {
                "fieldname": "peso_bruto",
                "label": "Peso Bruto Total (kg)",
                "fieldtype": "Float",
                "precision": "3",
                "insert_after": "peso_liquido"
            }
        ]
    }
