frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        // Indicador de status fiscal no cabeçalho
        if (frm.doc.status_fiscal === 'Autorizada') {
            frm.dashboard.add_indicator(__('NF-e Autorizada: Nº {0}', [frm.doc.numero_nfe]), 'green');
            
            // Botão direto para Imprimir DANFE
            frm.add_custom_button(__('Imprimir DANFE (PDF)'), function() {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?sales_order=' + encodeURIComponent(frm.doc.name));
            }, __('Ações Fiscais')).addClass('btn-primary');

            // Botão para ver documento fiscal
            frm.add_custom_button(__('Ver Documento Fiscal (NF-e)'), function() {
                frappe.set_route('Form', 'Documento Fiscal Eletronico', frm.doc.documento_fiscal);
            }, __('Ações Fiscais'));
        }

        // Botão para Faturamento Individual do Pedido de Venda
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Closed' && frm.doc.status_fiscal !== 'Autorizada') {
            frm.add_custom_button(__('Faturar e Emitir NF-e'), function() {
                frm.trigger('executar_faturamento_individual');
            }, __('Ações Fiscais')).addClass('btn-primary');
        }
    },

    executar_faturamento_individual: function(frm) {
        let msg = `
            <div style="font-size: 13px;">
                <p>Confirma o faturamento individual do pedido <b>${frm.doc.name}</b> e a transmissão da NF-e para a SEFAZ?</p>
                <div style="background: #f9fafb; padding: 10px; border: 1px solid #e5e7eb; border-radius: 4px;">
                    <div><b>Cliente:</b> ${frm.doc.customer_name || frm.doc.customer}</div>
                    <div><b>Valor Total:</b> ${format_currency(frm.doc.grand_total, frm.doc.currency)}</div>
                    <div><b>Volumes:</b> ${frm.doc.volumes || 1} cx/vol</div>
                    <div><b>Peso Líquido:</b> ${(frm.doc.peso_liquido || 0).toFixed(3)} kg</div>
                    <div><b>Peso Bruto:</b> ${(frm.doc.peso_bruto || 0).toFixed(3)} kg</div>
                </div>
            </div>
        `;

        frappe.confirm(msg, function() {
            frappe.dom.freeze(__('Faturando pedido e emitindo NF-e na SEFAZ... Por favor aguarde.'));
            
            frappe.call({
                method: 'erpz_fiscal.api.nfe.faturar_sales_order_individual',
                args: { sales_order: frm.doc.name },
                callback: function(r) {
                    frappe.dom.unfreeze();
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        
                        let d = new frappe.ui.Dialog({
                            title: __('NF-e Emitida com Sucesso!'),
                            indicator: 'green',
                            fields: [
                                {
                                    fieldtype: 'HTML',
                                    fieldname: 'msg_html',
                                    options: `
                                        <div style="padding: 10px; text-align: center;">
                                            <h4 style="color: #15803d; margin-bottom: 5px;">Nota Fiscal Autorizada: Nº ${r.message.numero_nfe}</h4>
                                            <p style="color: #4b5563; font-size: 11px;">Chave: ${r.message.chave_nfe}</p>
                                            <p style="color: #6b7280; font-size: 12px;">Fatura Gerada: <b>${r.message.sales_invoice}</b></p>
                                        </div>
                                    `
                                }
                            ],
                            primary_action_label: __('Imprimir DANFE (PDF)'),
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
                        frm.reload_doc();
                        frappe.msgprint({
                            title: __('Retorno da SEFAZ: NF-e Rejeitada'),
                            indicator: 'red',
                            message: `
                                <div class="p-2">
                                    <h5 class="text-danger font-weight-bold mb-2">A SEFAZ não autorizou o documento fiscal</h5>
                                    <div class="alert alert-danger p-2 mb-3 font-weight-bold" style="font-size: 13px;">
                                        ${r.message.mensagem}
                                    </div>
                                    <table class="table table-bordered small">
                                        <tr><th style="width: 35%;">Documento Gerado</th><td><a href="/desk/documento-fiscal-eletronico/${r.message.documento_fiscal}" target="_blank"><b>${r.message.documento_fiscal}</b></a></td></tr>
                                        <tr><th>Chave de Acesso</th><td><code>${r.message.chave_nfe}</code></td></tr>
                                        <tr><th>Fatura Gerada</th><td>${r.message.sales_invoice}</td></tr>
                                        <tr><th>Situação</th><td><span class="badge badge-danger font-weight-bold">Rejeitada na SEFAZ</span></td></tr>
                                    </table>
                                </div>
                            `
                        });
                    }
                },
                error: function(err) {
                    frappe.dom.unfreeze();
                    frappe.msgprint(__('Erro no faturamento: ') + (err.message || err));
                }
            });
        });
    }
});
