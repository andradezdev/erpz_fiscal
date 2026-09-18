frappe.ui.form.on('Nota Fiscal de Servico Eletronica', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.status === 'Autorizada') {
            frm.dashboard.add_indicator(__('NFS-e Autorizada: Nº {0}', [frm.doc.numero_nfse]), 'green');

            frm.add_custom_button(__('Imprimir DANFSE'), function() {
                frappe.utils.print(frm.doc.doctype, frm.doc.name, 'DANFSE (Padrão Nacional / ABRASF)');
            }).addClass('btn-primary');

            if (frm.doc.link_visualizacao_prefeitura) {
                frm.add_custom_button(__('Ver no Portal da Prefeitura'), function() {
                    window.open(frm.doc.link_visualizacao_prefeitura, '_blank');
                });
            }
        }

        if (!frm.is_new() && frm.doc.status !== 'Autorizada' && frm.doc.status !== 'Cancelada') {
            frm.add_custom_button(__('Transmitir para Prefeitura'), function() {
                frappe.dom.freeze(__('Transmitindo NFS-e para o Web Service da Prefeitura...'));
                frm.call({
                    method: 'transmitir_prefeitura',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('NFS-e Emitida com Sucesso!'),
                                indicator: 'green',
                                message: `<b>Nº NFS-e:</b> ${r.message.numero_nfse}<br><b>Código de Verificação:</b> ${r.message.codigo_verificacao}`
                            });
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    },

    valor_servicos: (frm) => frm.trigger('calcular_totais'),
    valor_deducoes: (frm) => frm.trigger('calcular_totais'),
    valor_desconto: (frm) => frm.trigger('calcular_totais'),
    aliquota_iss: (frm) => frm.trigger('calcular_totais'),
    iss_retido: (frm) => frm.trigger('calcular_totais'),
    valor_pis: (frm) => frm.trigger('calcular_totais'),
    valor_cofins: (frm) => frm.trigger('calcular_totais'),
    valor_inss: (frm) => frm.trigger('calcular_totais'),
    valor_irrf: (frm) => frm.trigger('calcular_totais'),
    valor_csll: (frm) => frm.trigger('calcular_totais'),

    calcular_totais: function(frm) {
        let vl_serv = flt(frm.doc.valor_servicos);
        let vl_ded = flt(frm.doc.valor_deducoes);
        let vl_desc = flt(frm.doc.valor_desconto);
        let base_iss = Math.max(0, vl_serv - vl_ded - vl_desc);
        let aliq_iss = flt(frm.doc.aliquota_iss || 2.9);
        let vl_iss = base_iss * (aliq_iss / 100);

        let tot_ret = flt(frm.doc.valor_pis) + flt(frm.doc.valor_cofins) + flt(frm.doc.valor_inss) + flt(frm.doc.valor_irrf) + flt(frm.doc.valor_csll);
        if (frm.doc.iss_retido) tot_ret += vl_iss;

        frm.set_value('base_calculo_iss', base_iss);
        frm.set_value('valor_iss', vl_iss);
        frm.set_value('total_retencoes', tot_ret);
        frm.set_value('valor_liquido', Math.max(0, vl_serv - tot_ret - vl_desc));

        frm.set_value('valor_ibs', vl_serv * (flt(frm.doc.aliquota_ibs || 17.7) / 100));
        frm.set_value('valor_cbs', vl_serv * (flt(frm.doc.aliquota_cbs || 8.8) / 100));
    }
});
