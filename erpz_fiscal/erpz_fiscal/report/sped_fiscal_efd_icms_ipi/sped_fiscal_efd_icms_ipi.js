frappe.query_reports["SPED Fiscal EFD ICMS IPI"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1 },
        { "fieldname": "from_date", "label": __("Data Inicial"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "reqd": 1 },
        { "fieldname": "to_date", "label": __("Data Final"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "reqd": 1 }
    ]
};
