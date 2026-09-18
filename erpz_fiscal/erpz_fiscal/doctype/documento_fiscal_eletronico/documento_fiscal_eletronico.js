frappe.ui.form.on('Documento Fiscal Eletronico', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.status === 'Autorizado') {
            let is_nfce = (frm.doc.modelo_fiscal || "").includes("65");
            let btn_label = is_nfce ? __('Imprimir Cupom NFC-e (80mm)') : __('Imprimir DANFE (PDF)');

            frm.add_custom_button(btn_label, function() {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?documento_fiscal=' + encodeURIComponent(frm.doc.name));
            }).addClass('btn-primary');
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
