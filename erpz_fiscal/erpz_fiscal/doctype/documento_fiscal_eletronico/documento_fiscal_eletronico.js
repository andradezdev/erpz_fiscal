frappe.ui.form.on('Documento Fiscal Eletronico', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.status === 'Rejeitado') {
            let cod = frm.doc.codigo_status_sefaz || '';
            let mot = frm.doc.motivo_rejeicao || frm.doc.mensagem_sefaz || __('Documento fiscal rejeitado pela SEFAZ');
            frm.dashboard.set_headline(`
                <div class="alert alert-danger mb-0 font-weight-bold" style="font-size: 13px;">
                    <i class="octicon octicon-alert mr-1"></i> Rejeição da SEFAZ [cStat ${cod}]: ${mot}
                </div>
            `);
            frm.dashboard.add_indicator(__('Rejeitado na SEFAZ ({0})', [cod]), 'red');
        }
        if (!frm.is_new() && frm.doc.status === 'Autorizado') {
            let is_nfce = (frm.doc.modelo_fiscal || "").includes("65");
            let btn_label = is_nfce ? __('Imprimir Cupom NFC-e (80mm)') : __('Imprimir DANFE (PDF)');

            frm.add_custom_button(btn_label, function() {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?documento_fiscal=' + encodeURIComponent(frm.doc.name));
            }).addClass('btn-primary');
        }

        
        if (!frm.is_new() && frm.doc.status === 'Autorizado') {
            frm.add_custom_button(__('Cancelar NF-e na SEFAZ'), function() {
                frappe.prompt(
                    {
                        fieldname: 'justificativa',
                        fieldtype: 'Small Text',
                        label: __('Justificativa do Cancelamento (Mínimo 15 caracteres)'),
                        reqd: 1
                    },
                    function(values) {
                        frappe.dom.freeze(__('Enviando evento de cancelamento para a SEFAZ...'));
                        frm.call({
                            method: 'cancelar_documento_sefaz',
                            doc: frm.doc,
                            args: { justificativa: values.justificativa },
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                frm.reload_doc();
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Cancelamento Homologado pela SEFAZ'),
                                        indicator: 'green',
                                        message: `<b>Status:</b> ${r.message.xMotivo}<br><b>Protocolo:</b> ${r.message.protocolo}`
                                    });
                                }
                            }
                        });
                    },
                    __('Cancelar Documento Fiscal na SEFAZ'),
                    __('Confirmar Cancelamento')
                );
            }, __('Ações SEFAZ'));

            frm.add_custom_button(__('Carta de Correção (CC-e)'), function() {
                frappe.prompt(
                    {
                        fieldname: 'texto_correcao',
                        fieldtype: 'Small Text',
                        label: __('Texto da Correção (15 a 1000 caracteres)'),
                        description: __('A CC-e não pode alterar valores, alíquotas, impostos, data de emissão ou dados do destinatário.'),
                        reqd: 1
                    },
                    function(values) {
                        frappe.dom.freeze(__('Transmitindo Carta de Correção para a SEFAZ...'));
                        frm.call({
                            method: 'emitir_cce_sefaz',
                            doc: frm.doc,
                            args: { texto_correcao: values.texto_correcao },
                            callback: function(r) {
                                frappe.dom.unfreeze();
                                frm.reload_doc();
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Carta de Correção Homologada'),
                                        indicator: 'green',
                                        message: `<b>Status:</b> ${r.message.xMotivo}<br><b>Sequencial:</b> ${r.message.sequencial}<br><b>Protocolo:</b> ${r.message.protocolo}`
                                    });
                                }
                            }
                        });
                    },
                    __('Emitir Carta de Correção Eletrônica (CC-e)'),
                    __('Transmitir CC-e')
                );
            }, __('Ações SEFAZ'));
        }

        if (!frm.is_new() && frm.doc.chave_acesso) {
            frm.add_custom_button(__('Consultar Situação na SEFAZ'), function() {
                frappe.dom.freeze(__('Consultando situação do documento fiscal na SEFAZ...'));
                frappe.call({
                    method: 'erpz_fiscal.api.nfe.consultar_documento_sefaz',
                    args: { documento_fiscal: frm.doc.name },
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        if (r.message) {
                            let m = r.message;
                            let ind = m.cStat === '100' ? 'green' : (m.cStat === '101' ? 'orange' : 'red');
                            frappe.msgprint({
                                title: __('Retorno Oficial da SEFAZ'),
                                indicator: ind,
                                message: `
                                    <div class="p-2">
                                        <table class="table table-bordered mb-0">
                                            <tr><th style="width: 35%;">Status SEFAZ (cStat)</th><td><span class="badge badge-${m.cStat === '100' ? 'success' : 'danger'} font-weight-bold" style="font-size: 13px;">${m.cStat}</span></td></tr>
                                            <tr><th>Mensagem / Motivo</th><td><b>${m.xMotivo}</b></td></tr>
                                            <tr><th>Chave de Acesso</th><td><code>${m.chave_acesso}</code></td></tr>
                                            <tr><th>Protocolo</th><td>${m.protocolo || 'Não gerado'}</td></tr>
                                            <tr><th>Ambiente</th><td>${m.ambiente || 'Homologação'}</td></tr>
                                        </table>
                                    </div>
                                `
                            });
                            frm.reload_doc();
                        }
                    }
                });
            });
        }

        if (!frm.is_new() && frm.doc.status !== 'Autorizado' && frm.doc.status !== 'Cancelado') {
            let is_nfce = (frm.doc.modelo_fiscal || "").includes("65");
            let emit_label = is_nfce ? __('Transmitir NFC-e para SEFAZ') : __('Transmitir NF-e para SEFAZ');

            frm.add_custom_button(emit_label, function() {
                frappe.dom.freeze(__('Transmitindo documento fiscal para a SEFAZ...'));
                frm.call({
                    method: 'transmitir_sefaz',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: is_nfce ? __('NFC-e Autorizada com Sucesso!') : __('NF-e Autorizada com Sucesso!'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    }
});
