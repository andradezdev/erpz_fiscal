frappe.ui.form.on('Importacao NFe Compra', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Botões de geração de documentos
            if (!frm.doc.purchase_receipt && !frm.doc.purchase_invoice) {
                frm.add_custom_button(__('Gerar Ambos (Estoque + Fatura)'), function() {
                    frappe.confirm(__('Confirma a geração da Entrada de Estoque e da Fatura de Compra no ERPNext?'), function() {
                        frappe.dom.freeze(__('Gerando Entrada no Estoque e Fatura de Compra...'));
                        frm.call({
                            method: 'gerar_ambos',
                            doc: frm.doc,
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                frm.reload_doc();
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Documentos gerados com sucesso!'),
                                        indicator: 'green'
                                    });
                                }
                            }
                        });
                    });
                }, __('Gerar Documentos')).addClass('btn-primary');
            }

            if (!frm.doc.purchase_receipt) {
                frm.add_custom_button(__('Gerar Entrada de Estoque (Purchase Receipt)'), function() {
                    frappe.dom.freeze(__('Gerando Entrada no Estoque...'));
                    frm.call({
                        method: 'gerar_purchase_receipt',
                        doc: frm.doc,
                        callback: function(r) {
                            frappe.dom.unfreeze();
                            frm.reload_doc();
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __('Entrada de Estoque gerada: ' + r.message.purchase_receipt),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }, __('Gerar Documentos'));
            }

            if (!frm.doc.purchase_invoice) {
                frm.add_custom_button(__('Gerar Fatura de Compra (Purchase Invoice)'), function() {
                    frappe.dom.freeze(__('Gerando Fatura de Compra...'));
                    frm.call({
                        method: 'gerar_purchase_invoice',
                        doc: frm.doc,
                        callback: function(r) {
                            frappe.dom.unfreeze();
                            frm.reload_doc();
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __('Fatura de Compra gerada: ' + r.message.purchase_invoice),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }, __('Gerar Documentos'));
            }

            // Botão para memorizar De-Para
            frm.add_custom_button(__('Salvar Memória De-Para'), function() {
                frm.call({
                    method: 'salvar_mapeamentos_itens',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Mapeamentos de itens salvos com sucesso! (' + r.message.saved_count + ' itens)'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, __('Ações'));

            // Reprocessar XML
            frm.add_custom_button(__('Reprocessar XML'), function() {
                frappe.dom.freeze(__('Reprocessando XML...'));
                frm.call({
                    method: 'processar_xml',
                    doc: frm.doc,
                    callback: function() {
                        frappe.dom.unfreeze();
                        frm.save();
                    }
                });
            }, __('Ações'));
        }
    }
});
