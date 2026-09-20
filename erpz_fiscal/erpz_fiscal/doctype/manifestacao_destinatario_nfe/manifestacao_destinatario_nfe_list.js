frappe.listview_settings['Manifestacao Destinatario NFe'] = {
    add_fields: ["situacao_manifestacao", "tem_xml_completo", "valor_total"],
    get_indicator: function(doc) {
        if (doc.tem_xml_completo) {
            return [__("XML Baixado"), "green", "tem_xml_completo,=,1"];
        } else if (doc.situacao_manifestacao && doc.situacao_manifestacao !== "Sem Manifestação") {
            return [__(doc.situacao_manifestacao), "orange", "situacao_manifestacao,!=,Sem Manifestação"];
        } else {
            return [__("Pendente"), "gray", "situacao_manifestacao,=,Sem Manifestação"];
        }
    },
    onload: function(listview) {
        listview.page.add_inner_button(__('Buscar Notas na SEFAZ (MDe)'), function() {
            frappe.dom.freeze(__('Consultando notas emitidas contra o CNPJ na SEFAZ Nacional...'));
            frappe.call({
                method: 'erpz_fiscal.api.nfe.sincronizar_mde_sefaz',
                callback: function(r) {
                    frappe.dom.unfreeze();
                    listview.refresh();
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Retorno da SEFAZ Nacional'),
                            indicator: 'green',
                            message: `<b>Status:</b> ${r.message.xMotivo} (cStat ${r.message.cStat})<br><b>Novas Notas Encontradas:</b> ${r.message.novas_notas}<br><b>Último NSU Consultado:</b> ${r.message.ultimo_nsu}`
                        });
                    }
                }
            });
        }).addClass('btn-primary');
    }
};
