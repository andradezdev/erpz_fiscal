frappe.query_reports["Relatorio de Cargas e Faturamento"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company") },
        { "fieldname": "carga", "label": __("Carga"), "fieldtype": "Link", "options": "Montagem de Carga" },
        { "fieldname": "status_carga", "label": __("Status Carga"), "fieldtype": "Select", "options": "\nRascunho\nEm Aberto\nEm Carregamento\nFaturada\nFinalizada" }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "status_faturamento") {
            if (data.status_faturamento === "Faturado") value = `<span class="indicator-pill green">${value}</span>`;
            else if (data.status_faturamento === "Erro") value = `<span class="indicator-pill red">${value}</span>`;
            else value = `<span class="indicator-pill orange">${value}</span>`;
        }
        return value;
    }
};
