frappe.query_reports["EFD Contribuicoes PIS COFINS"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1 },
        { "fieldname": "from_date", "label": __("Data Inicial"), "fieldtype": "Date", "default": frappe.datetime.month_start(), "reqd": 1 },
        { "fieldname": "to_date", "label": __("Data Final"), "fieldtype": "Date", "default": frappe.datetime.month_end(), "reqd": 1 }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__('Exportar Arquivo TXT (PVA EFD Contribuições)'), function() {
            let filters = report.get_values();
            frappe.dom.freeze(__('Gerando arquivo TXT da EFD Contribuições...'));
            frappe.call({
                method: 'erpz_fiscal.api.nfe.baixar_arquivo_efd_contribuicoes_txt',
                args: {
                    empresa: filters.empresa,
                    from_date: filters.from_date,
                    to_date: filters.to_date
                },
                callback: function(r) {
                    frappe.dom.unfreeze();
                    if (r.message && r.message.conteudo_txt) {
                        let blob = new Blob([r.message.conteudo_txt], { type: 'text/plain;charset=latin1' });
                        let link = document.createElement('a');
                        link.href = URL.createObjectURL(blob);
                        link.download = r.message.nome_arquivo || 'EFD_CONTRIBUICOES.txt';
                        link.click();
                        frappe.show_alert({ message: __('Arquivo TXT gerado com sucesso!'), indicator: 'green' });
                    }
                },
                error: function() {
                    frappe.dom.unfreeze();
                }
            });
        }).addClass('btn-primary');
    }
};

// Aliases para cobrir busca com ou sem acentuação
frappe.query_reports["EFD Contribuições PIS COFINS"] = frappe.query_reports["EFD Contribuicoes PIS COFINS"];
