frappe.ui.form.on('Certificado Digital', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.status === 'Ativo') {
            frm.add_custom_button(__('Testar Conexão com SEFAZ'), function() {
                frappe.dom.freeze(__('Consultando status do WebService da SEFAZ...'));
                frappe.call({
                    method: 'erpz_fiscal.api.nfe.testar_conexao_sefaz',
                    args: {
                        empresa: frm.doc.empresa,
                        certificado_name: frm.doc.name
                    },
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        if (r.message) {
                            let m = r.message;
                            let ind = m.cStat === '107' ? 'green' : 'red';
                            frappe.msgprint({
                                title: __('Status do Serviço SEFAZ'),
                                indicator: ind,
                                message: `
                                    <div class="p-2">
                                        <table class="table table-bordered mb-0">
                                            <tr><th style="width: 35%;">Status (cStat)</th><td><span class="badge badge-${m.cStat === '107' ? 'success' : 'danger'} font-weight-bold" style="font-size: 13px;">${m.cStat}</span></td></tr>
                                            <tr><th>Retorno SEFAZ</th><td><b>${m.xMotivo}</b></td></tr>
                                            <tr><th>UF</th><td>${m.uf || 'SP'}</td></tr>
                                            <tr><th>Ambiente</th><td>${m.ambiente}</td></tr>
                                            <tr><th>Data/Hora Resposta</th><td>${m.dhRecbto || '-'}</td></tr>
                                            <tr><th>CNPJ do Certificado</th><td><code>${m.cnpj || '-'}</code></td></tr>
                                        </table>
                                    </div>
                                `
                            });
                        }
                    }
                });
            }).addClass('btn-primary');

            frm.add_custom_button(__('Consultar Cadastro CADESP (SEFAZ)'), function() {
                frappe.dom.freeze(__('Consultando situação cadastral do CNPJ na SEFAZ SP...'));
                frappe.call({
                    method: 'erpz_fiscal.api.nfe.consultar_cadastro_sefaz',
                    args: {
                        empresa: frm.doc.empresa,
                        cnpj: frm.doc.cnpj_certificado,
                        uf: 'SP'
                    },
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        if (r.message) {
                            let m = r.message;
                            let ind = m.cStat === '111' ? 'green' : 'orange';
                            let cad = m.dados_cadastrais || {};
                            frappe.msgprint({
                                title: __('Situação Cadastral no CADESP / SEFAZ'),
                                indicator: ind,
                                message: `
                                    <div class="p-2">
                                        <table class="table table-bordered mb-0">
                                            <tr><th style="width: 35%;">Status (cStat)</th><td><b>${m.cStat}</b></td></tr>
                                            <tr><th>Motivo SEFAZ</th><td><b>${m.xMotivo}</b></td></tr>
                                            <tr><th>CNPJ Consultado</th><td><code>${m.cnpj}</code></td></tr>
                                            ${cad.xNome ? `<tr><th>Razão Social</th><td>${cad.xNome}</td></tr>` : ''}
                                            ${cad.IE ? `<tr><th>Inscrição Estadual</th><td><b>${cad.IE}</b></td></tr>` : ''}
                                            ${cad.cSit ? `<tr><th>Situação Cadastral</th><td>${cad.cSit === '1' ? 'Habilitado' : 'Não Habilitado'}</td></tr>` : ''}
                                        </table>
                                    </div>
                                `
                            });
                        }
                    }
                });
            });
        }
    }
});
