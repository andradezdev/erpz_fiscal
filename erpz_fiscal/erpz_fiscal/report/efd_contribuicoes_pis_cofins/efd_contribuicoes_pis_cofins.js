frappe.query_reports["EFD Contribuições PIS COFINS"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company") },
        { "fieldname": "from_date", "label": __("Data Inicial"), "fieldtype": "Date", "default": frappe.datetime.month_start() },
        { "fieldname": "to_date", "label": __("Data Final"), "fieldtype": "Date", "default": frappe.datetime.month_end() }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__('Exportar Arquivo TXT (PVA)'), function() {
            let data = report.data;
            if (!data || data.length === 0) {
                frappe.msgprint(__('Nenhum dado gerado para exportar.'));
                return;
            }
            let txt = data.map(d => d.linha).join('\r\n') + '\r\n';
            let blob = new Blob([txt], { type: 'text/plain;charset=latin1' });
            let link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'EFD_CONTRIBUICOES_' + frappe.datetime.get_today().replace(/-/g, '') + '.txt';
            link.click();
        }).addClass('btn-primary');
    }
};
