frappe.ui.form.on('POS Invoice', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // 1. Caso Autorizada
            if (frm.doc.status_fiscal === 'Autorizada') {
                frm.dashboard.add_indicator(__('NFC-e Autorizada: Nº {0}', [frm.doc.numero_nfe || '']), 'green');

                frm.add_custom_button(__('Imprimir Cupom NFC-e (80mm)'), function() {
                    window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(frm.doc.name));
                }, __('Ações Fiscais')).addClass('btn-primary');

                frm.add_custom_button(__('Ver Documento Fiscal (NFC-e)'), function() {
                    frappe.set_route('Form', 'Documento Fiscal Eletronico', frm.doc.documento_fiscal);
                }, __('Ações Fiscais'));

                frm.add_custom_button(__('Consultar Situação na SEFAZ'), function() {
                    frappe.call({
                        method: 'erpz_fiscal.api.nfe.consultar_documento_sefaz',
                        args: { documento_fiscal: frm.doc.documento_fiscal },
                        callback: function(r) {
                            if (r.message) {
                                let m = r.message;
                                let ind = m.cStat === '100' ? 'green' : (m.cStat === '101' ? 'orange' : 'red');
                                frappe.msgprint({
                                    title: __('Retorno Oficial SEFAZ'),
                                    indicator: ind,
                                    message: `
                                        <div class="p-2">
                                            <table class="table table-bordered mb-0 small">
                                                <tr><th style="width: 35%;">Status SEFAZ (cStat)</th><td><b>${m.cStat}</b></td></tr>
                                                <tr><th>Mensagem / Motivo</th><td><b>${m.xMotivo}</b></td></tr>
                                                <tr><th>Chave NFC-e</th><td><code>${m.chave_acesso}</code></td></tr>
                                                <tr><th>Protocolo</th><td>${m.protocolo || '-'}</td></tr>
                                            </table>
                                        </div>
                                    `
                                });
                            }
                        }
                    });
                }, __('Ações Fiscais'));
            }

            // 2. Caso Rejeitada
            if (frm.doc.status_fiscal === 'Rejeitada') {
                frm.dashboard.add_indicator(__('NFC-e Rejeitada na SEFAZ'), 'red');

                frm.add_custom_button(__('Tentar Reemitir NFC-e'), function() {
                    frm.trigger('executar_emissao_nfce');
                }, __('Ações Fiscais')).addClass('btn-danger');
            }

            // 3. Caso Submetida sem NFC-e ou Pendente
            if (frm.doc.docstatus === 1 && frm.doc.status_fiscal !== 'Autorizada' && frm.doc.status_fiscal !== 'Rejeitada') {
                frm.add_custom_button(__('Emitir NFC-e (Mod. 65)'), function() {
                    frm.trigger('executar_emissao_nfce');
                }, __('Ações Fiscais')).addClass('btn-primary');
            }
        }
    },

    executar_emissao_nfce: function(frm) {
        frappe.dom.freeze(__('Transmitindo NFC-e para a SEFAZ...'));
        frappe.call({
            method: 'erpz_fiscal.api.nfe.emitir_nfce_pos_invoice',
            args: { pos_invoice: frm.doc.name },
            callback: function(r) {
                frappe.dom.unfreeze();
                frm.reload_doc();

                if (r.message && r.message.success) {
                    let d = new frappe.ui.Dialog({
                        title: __('NFC-e Emitida com Sucesso!'),
                        indicator: 'green',
                        fields: [
                            {
                                fieldtype: 'HTML',
                                fieldname: 'html_info',
                                options: `
                                    <div style="padding: 10px; text-align: center;">
                                        <h4 style="color: #15803d; margin-bottom: 5px;">NFC-e Autorizada: Nº ${r.message.numero_nfe}</h4>
                                        <p style="color: #4b5563; font-size: 11px;">Chave: ${r.message.chave_nfe}</p>
                                        <p style="color: #6b7280; font-size: 12px;">Venda PDV: <b>${r.message.pos_invoice}</b></p>
                                    </div>
                                `
                            }
                        ],
                        primary_action_label: __('Imprimir Cupom NFC-e (80mm)'),
                        primary_action: function() {
                            d.hide();
                            window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?documento_fiscal=' + encodeURIComponent(r.message.documento_fiscal));
                        },
                        secondary_action_label: __('Ver Documento Fiscal'),
                        secondary_action: function() {
                            d.hide();
                            frappe.set_route('Form', 'Documento Fiscal Eletronico', r.message.documento_fiscal);
                        }
                    });
                    d.show();
                } else if (r.message) {
                    frappe.msgprint({
                        title: __('Retorno da SEFAZ: NFC-e Rejeitada'),
                        indicator: 'red',
                        message: `
                            <div class="p-2">
                                <h5 class="text-danger font-weight-bold mb-2">A SEFAZ rejeitou a emissão da NFC-e</h5>
                                <div class="alert alert-danger p-2 mb-3 font-weight-bold" style="font-size: 13px;">
                                    ${r.message.mensagem}
                                </div>
                                <table class="table table-bordered small">
                                    <tr><th style="width: 35%;">Documento Fiscal</th><td><a href="/desk/documento-fiscal-eletronico/${r.message.documento_fiscal}" target="_blank"><b>${r.message.documento_fiscal}</b></a></td></tr>
                                    <tr><th>Chave de Acesso</th><td><code>${r.message.chave_nfe}</code></td></tr>
                                    <tr><th>Fatura do PDV</th><td>${r.message.pos_invoice}</td></tr>
                                    <tr><th>Situação</th><td><span class="badge badge-danger">Rejeitada</span></td></tr>
                                </table>
                            </div>
                        `
                    });
                }
            },
            error: function(err) {
                frappe.dom.unfreeze();
                frappe.msgprint(__('Erro ao emitir NFC-e: ') + (err.message || err));
            }
        });
    }
});
