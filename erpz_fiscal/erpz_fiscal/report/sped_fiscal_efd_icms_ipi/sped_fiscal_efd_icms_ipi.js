frappe.query_reports["SPED Fiscal EFD ICMS IPI"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1 },
        { "fieldname": "from_date", "label": __("Data Inicial"), "fieldtype": "Date", "default": frappe.datetime.month_start(), "reqd": 1 },
        { "fieldname": "to_date", "label": __("Data Final"), "fieldtype": "Date", "default": frappe.datetime.month_end(), "reqd": 1 },
        { "fieldname": "gerar_bloco_k", "label": __("Incluir Bloco K (MRP / Produção)"), "fieldtype": "Check", "default": 1 },
        { 
            "fieldname": "filtrar_bloco", 
            "label": __("Visualizar Bloco na Grade"), 
            "fieldtype": "Select", 
            "options": "\nTodos os Blocos\nBloco K - Controle da Produção e Estoque (MRP)\nBloco C - Documentos Fiscais (NF-e/NFC-e)\nBloco E - Apuração do ICMS\nBloco 0 - Abertura e Cadastros\nBloco 9 - Totalizadores e Encerramento",
            "default": "Todos os Blocos"
        }
    ],

    "onload": function(report) {
        // Botão de Download direto do arquivo TXT para o PVA da Receita Federal
        report.page.add_inner_button(__('Exportar Arquivo TXT (PVA SPED Fiscal)'), function() {
            let filters = report.get_values();
            frappe.call({
                method: 'erpz_fiscal.api.nfe.baixar_arquivo_sped_fiscal_txt',
                args: {
                    empresa: filters.empresa,
                    from_date: filters.from_date,
                    to_date: filters.to_date,
                    gerar_bloco_k: filters.gerar_bloco_k
                },
                callback: function(r) {
                    if (r.message && r.message.conteudo_txt) {
                        let blob = new Blob([r.message.conteudo_txt], { type: 'text/plain;charset=latin1' });
                        let link = document.createElement('a');
                        link.href = URL.createObjectURL(blob);
                        link.download = r.message.nome_arquivo || 'SPED_EFD_ICMS_IPI.txt';
                        link.click();
                        frappe.show_alert({ message: __('Arquivo TXT gerado com sucesso!'), indicator: 'green' });
                    }
                }
            });
        }).addClass('btn-primary');
    }
};
