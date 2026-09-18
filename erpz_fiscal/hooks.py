app_name = "erpz_fiscal"
app_title = "ERPZ Fiscal"
app_publisher = "ERPZ"
app_description = "Localização Fiscal Brasileira Oficial - Motor Tributário, NFe 4.0, NFCe, DANFE, SPED e Montagem de Carga"
app_email = "dev@erpz.io"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["frappe", "erpnext"]

# Instalação e Migração
after_install = "erpz_fiscal.setup.after_install"
after_migrate = "erpz_fiscal.setup.after_migrate"

# Client Scripts dos DocTypes
doctype_js = {
    "Sales Order": "public/js/sales_order.js",
    "POS Invoice": "public/js/pos_invoice.js"
}

# Document Events
doc_events = {
    "Sales Order": {
        "validate": "erpz_fiscal.api.nfe.calcular_pesos_sales_order"
    },
    "Sales Invoice": {
        "on_cancel": "erpz_fiscal.api.nfe.validar_cancelamento_fatura"
    },
    "POS Invoice": {
        "on_submit": "erpz_fiscal.api.nfe.pos_invoice_on_submit"
    }
}

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["module", "=", "ERPZ Fiscal"]]
    }
]

app_include_js = "/assets/erpz_fiscal/js/erpz_fiscal.js"
