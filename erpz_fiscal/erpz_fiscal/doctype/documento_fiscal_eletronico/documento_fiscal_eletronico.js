frappe.ui.form.on('Documento Fiscal Eletronico', {
    
    onload: function(frm) {
        frm.trigger('carregar_opcoes_nfe_referenciada');
    },

    reter_csrf: function(frm) { frm.trigger('recalcular_totais_client'); },
    reter_irrf: function(frm) { frm.trigger('recalcular_totais_client'); },
    reter_inss: function(frm) { frm.trigger('recalcular_totais_client'); },
    destinatario_uf: function(frm) { frm.trigger('recalcular_totais_client'); },
    destinatario_consumidor_final: function(frm) { frm.trigger('recalcular_totais_client'); },
    destinatario_indicador_ie: function(frm) { frm.trigger('recalcular_totais_client'); },

    finalidade_emissao: function(frm) {
        frm.trigger('verificar_exigencia_nfe_referenciada');
    },

    verificar_exigencia_nfe_referenciada: function(frm) {
        const fin = frm.doc.finalidade_emissao || '';
        const exigida = fin.startsWith('4') || fin.startsWith('2'); // Devolução ou Complementar
        frm.set_df_property('chave_nfe_referenciada', 'reqd', exigida ? 1 : 0);
    },

    recalcular_totais_client: function(frm) {
        frm.call({
            method: 'calcular_totais',
            doc: frm.doc,
            callback: function() {
                frm.refresh_fields();
            }
        });
    },

    carregar_opcoes_nfe_referenciada: function(frm) {
        frappe.call({
            method: 'erpz_fiscal.erpz_fiscal.doctype.documento_fiscal_eletronico.documento_fiscal_eletronico.get_nfe_compra_referenciadas',
            args: { empresa: frm.doc.empresa },
            callback: function(r) {
                if (r.message && Array.isArray(r.message)) {
                    frm._nfe_compra_cache = r.message;
                    // Define as opções para o campo Autocomplete
                    frm.set_df_property('chave_nfe_referenciada', 'options', r.message);
                    frm.trigger('render_nfe_referenciada_helper');
                }
            }
        });
    },

    render_nfe_referenciada_helper: function(frm) {
        if (!frm.fields_dict.chave_nfe_referenciada) return;
        const $wrapper = frm.fields_dict.chave_nfe_referenciada.$wrapper;
        $wrapper.find('.nfe-ref-helper-area').remove();

        const $helper = $(`
            <div class="nfe-ref-helper-area mt-1 d-flex align-items-center justify-content-between" style="font-size: 12px;">
                <span class="text-muted">
                    <i class="octicon octicon-info mr-1"></i> Digite para buscar ou selecione na lista suspensa.
                </span>
                <button type="button" class="btn btn-xs btn-default btn-abrir-modal-nfe-compra" style="font-weight: 600; cursor: pointer;">
                    <i class="octicon octicon-search mr-1"></i> Selecionar de NF-e Importada de Compra
                </button>
            </div>
        `);

        $helper.find('.btn-abrir-modal-nfe-compra').on('click', function(e) {
            e.preventDefault();
            frm.trigger('abrir_dialog_selecao_nfe_compra');
        });

        $wrapper.append($helper);
    },

    abrir_dialog_selecao_nfe_compra: function(frm) {
        const itens = frm._nfe_compra_cache || [];
        if (!itens.length) {
            frappe.msgprint(__('Nenhuma NF-e de Compra com chave válida foi encontrada no sistema. Faça a importação prévia do XML na tela de Importação de NF-e de Compra.'));
            return;
        }

        let linhasHtml = '';
        itens.forEach(it => {
            linhasHtml += `
                <tr style="cursor: pointer;" class="linha-nfe-compra" data-chave="${it.chave_acesso}">
                    <td class="font-weight-bold text-center">NF ${it.numero_nota || '-'}</td>
                    <td><b>${it.fornecedor}</b></td>
                    <td class="text-center">${it.data_emissao || '-'}</td>
                    <td class="text-right font-weight-bold text-success">${it.valor}</td>
                    <td><code style="font-size: 11px;">${it.chave_acesso}</code></td>
                    <td class="text-center">
                        <button class="btn btn-xs btn-primary btn-selecionar-esta-chave" data-chave="${it.chave_acesso}">
                            Selecionar
                        </button>
                    </td>
                </tr>
            `;
        });

        const dialog = new frappe.ui.Dialog({
            title: __('Selecionar NF-e de Compra Importada para Referência'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'Data',
                    fieldname: 'busca',
                    label: __('Filtrar por Fornecedor, Número da Nota ou Chave'),
                    onchange: function() {
                        const val = (dialog.get_value('busca') || '').toLowerCase().trim();
                        dialog.$wrapper.find('.linha-nfe-compra').each(function() {
                            const text = $(this).text().toLowerCase();
                            $(this).toggle(text.includes(val));
                        });
                    }
                },
                {
                    fieldtype: 'HTML',
                    fieldname: 'tabela_html',
                    options: `
                        <div style="max-height: 400px; overflow-y: auto;">
                            <table class="table table-bordered table-hover mb-0" style="font-size: 12px;">
                                <thead class="thead-light">
                                    <tr>
                                        <th style="width: 12%; text-align: center;">Nota</th>
                                        <th style="width: 30%;">Fornecedor</th>
                                        <th style="width: 14%; text-align: center;">Emissão</th>
                                        <th style="width: 14%; text-align: right;">Total</th>
                                        <th style="width: 20%;">Chave de Acesso</th>
                                        <th style="width: 10%; text-align: center;">Ação</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${linhasHtml}
                                </tbody>
                            </table>
                        </div>
                    `
                }
            ]
        });

        dialog.show();

        dialog.$wrapper.find('.btn-selecionar-esta-chave, .linha-nfe-compra').on('click', function(e) {
            e.stopPropagation();
            const chave = $(this).data('chave') || $(this).closest('tr').data('chave');
            if (chave) {
                frm.set_value('chave_nfe_referenciada', chave);
                dialog.hide();
                frappe.show_alert({
                    message: __('Chave da NF-e vinculada com sucesso!'),
                    indicator: 'green'
                });
            }
        });
    },

    refresh: function(frm) {
        frm.trigger('verificar_exigencia_nfe_referenciada');
        frm.trigger('carregar_opcoes_nfe_referenciada');

        const is_nfce = (frm.doc.modelo_fiscal || "").includes("65");

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
            let btn_label = is_nfce ? __('Imprimir Cupom NFC-e (80mm)') : __('Imprimir DANFE (PDF)');

            frm.add_custom_button(btn_label, function() {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?documento_fiscal=' + encodeURIComponent(frm.doc.name));
            }).addClass('btn-primary');
        }

        if (!frm.is_new() && frm.doc.status === 'Autorizado') {
            let cancel_label = is_nfce ? __('Cancelar NFC-e na SEFAZ') : __('Cancelar NF-e na SEFAZ');

            frm.add_custom_button(cancel_label, function() {
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
                            always: function() {
                                frappe.dom.unfreeze();
                            },
                            callback: function(r) {
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
                    cancel_label,
                    __('Confirmar Cancelamento')
                );
            }, __('Ações SEFAZ'));

            // Carta de Correção é EXCLUSIVA de NF-e (Modelo 55), vedada para NFC-e (Modelo 65)
            if (!is_nfce) {
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
                                always: function() {
                                    frappe.dom.unfreeze();
                                },
                                callback: function(r) {
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
        }

        if (!frm.is_new() && frm.doc.chave_acesso) {
            frm.add_custom_button(__('Consultar Situação na SEFAZ'), function() {
                frappe.dom.freeze(__('Consultando situação do documento fiscal na SEFAZ...'));
                frappe.call({
                    method: 'erpz_fiscal.api.nfe.consultar_documento_sefaz',
                    args: { documento_fiscal: frm.doc.name },
                    always: function() {
                        frappe.dom.unfreeze();
                    },
                    callback: function(r) {
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
            let emit_label = is_nfce ? __('Transmitir NFC-e para SEFAZ') : __('Transmitir NF-e para SEFAZ');

            frm.add_custom_button(emit_label, function() {
                frappe.dom.freeze(__('Transmitindo documento fiscal para a SEFAZ...'));
                frm.call({
                    method: 'transmitir_sefaz',
                    doc: frm.doc,
                    always: function() {
                        frappe.dom.unfreeze();
                    },
                    callback: function(r) {
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
