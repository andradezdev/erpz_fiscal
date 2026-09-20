frappe.ui.form.on('Manifestacao Destinatario NFe', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Se ainda não deu ciência ou confirmação
            if (!frm.doc.situacao_manifestacao || frm.doc.situacao_manifestacao === 'Sem Manifestação') {
                frm.add_custom_button(__('Dar Ciência da Emissão (210210)'), function() {
                    frappe.dom.freeze(__('Enviando evento de Ciência para a SEFAZ...'));
                    frm.call({
                        method: 'dar_ciencia_emissao',
                        doc: frm.doc,
                        callback: function(r) {
                            frappe.dom.unfreeze();
                            frm.reload_doc();
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __('Ciência registrada na SEFAZ! XML baixado com sucesso.'),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }, __('Manifestação')).addClass('btn-primary');
            }

            frm.add_custom_button(__('Confirmar Operação (210200)'), function() {
                frappe.dom.freeze(__('Enviando Confirmação da Operação para a SEFAZ...'));
                frm.call({
                    method: 'confirmar_operacao',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Operação confirmada na SEFAZ com sucesso!'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, __('Manifestação'));

            frm.add_custom_button(__('Desconhecer Operação (210220)'), function() {
                frappe.confirm(__('Tem certeza que desconhece esta operação? A SEFAZ registrará o evento de contestação.'), function() {
                    frappe.dom.freeze(__('Enviando contestação para a SEFAZ...'));
                    frm.call({
                        method: 'desconhecer_operacao',
                        doc: frm.doc,
                        callback: function(r) {
                            frappe.dom.unfreeze();
                            frm.reload_doc();
                        }
                    });
                });
            }, __('Manifestação'));

            // Botão Baixar XML
            if (!frm.doc.tem_xml_completo) {
                frm.add_custom_button(__('Baixar XML da SEFAZ'), function() {
                    frappe.dom.freeze(__('Consultando SEFAZ Nacional para baixar XML...'));
                    frm.call({
                        method: 'baixar_xml_completo',
                        doc: frm.doc,
                        callback: function(r) {
                            frappe.dom.unfreeze();
                            frm.reload_doc();
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __('XML completo obtido com sucesso!'),
                                    indicator: 'green'
                                });
                            } else {
                                frappe.msgprint(__('Retorno SEFAZ: ') + (r.message ? r.message.xMotivo : 'XML ainda não liberado'));
                            }
                        }
                    });
                }, __('Ações'));
            }

            // Botão Criar Importação de Compra
            if (frm.doc.tem_xml_completo) {
                if (frm.doc.importacao_gerada) {
                    frm.add_custom_button(__('Abrir Importação de Compra'), function() {
                        frappe.set_route('Form', 'Importacao NFe Compra', frm.doc.importacao_gerada);
                    }).addClass('btn-primary');
                } else {
                    frm.add_custom_button(__('Importar para Estoque / Compras'), function() {
                        frappe.dom.freeze(__('Criando importação de compras a partir do XML...'));
                        frm.call({
                            method: 'criar_importacao_compra',
                            doc: frm.doc,
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                if (r.message && r.message.importacao) {
                                    frappe.set_route('Form', 'Importacao NFe Compra', r.message.importacao);
                                }
                            }
                        });
                    }).addClass('btn-primary');
                }
            }
        }
    }
});
