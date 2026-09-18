frappe.ui.form.on('Montagem de Carga', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Botão Adicionar Pedidos
            frm.add_custom_button(__('Adicionar Pedidos Abertos'), function() {
                frm.trigger('abrir_dialogo_pedidos');
            }, __('Ações da Carga'));

            // Botão Faturar Carga
            if (frm.doc.status !== 'Cancelada') {
                frm.add_custom_button(__('Faturar Carga'), function() {
                    frm.trigger('executar_faturamento_carga');
                }).addClass('btn-primary');
            }

            // Botões de Impressão Direta de Romaneios e Mapa de Carga
            frm.add_custom_button(__('Romaneio Sintético'), function() {
                let url = `/printview?doctype=Montagem%20de%20Carga&name=${encodeURIComponent(frm.doc.name)}&format=Romaneio%20de%20Carga%20-%20Sint%C3%A9tico&trigger_print=1`;
                window.open(url);
            }, __('Imprimir Romaneios'));

            frm.add_custom_button(__('Romaneio Analítico (Produtos)'), function() {
                let url = `/printview?doctype=Montagem%20de%20Carga&name=${encodeURIComponent(frm.doc.name)}&format=Romaneio%20de%20Carga%20-%20Anal%C3%ADtico%20(Com%20Produtos)&trigger_print=1`;
                window.open(url);
            }, __('Imprimir Romaneios'));

            frm.add_custom_button(__('Mapa de Carregamento (Baú)'), function() {
                let url = `/printview?doctype=Montagem%20de%20Carga&name=${encodeURIComponent(frm.doc.name)}&format=Mapa%20de%20Carregamento%20Consolidado&trigger_print=1`;
                window.open(url);
            }, __('Imprimir Romaneios'));

            frm.add_custom_button(__('Recalcular Totais'), function() {
                frm.trigger('recalcular_totais');
                frm.save();
            }, __('Ações da Carga'));
        }
    },

    abrir_dialogo_pedidos: function(frm) {
        if (!frm.doc.empresa) {
            frappe.msgprint(__('Selecione a Empresa antes de buscar pedidos.'));
            return;
        }

        new frappe.ui.form.MultiSelectDialog({
            doctype: 'Sales Order',
            target: frm,
            setters: { company: frm.doc.empresa, status: 'To Deliver and Bill' },
            date_field: 'transaction_date',
            get_query() {
                return {
                    filters: {
                        docstatus: 1,
                        company: frm.doc.empresa,
                        status: ['in', ['To Deliver and Bill', 'To Bill', 'To Deliver']]
                    }
                };
            },
            action(selections) {
                if (!selections || selections.length === 0) return;
                frappe.dom.freeze(__('Carregando dados dos pedidos...'));
                let promises = selections.map(so_name => {
                    let exists = (frm.doc.itens || []).some(r => r.sales_order === so_name);
                    if (exists) return Promise.resolve(null);
                    return frappe.call({
                        method: 'erpz_fiscal.erpz_fiscal.doctype.montagem_de_carga.montagem_de_carga.calcular_pesos_pedido',
                        args: { sales_order: so_name }
                    }).then(r => ({ so_name: so_name, data: r.message }));
                });

                Promise.all(promises).then(results => {
                    frappe.dom.unfreeze();
                    results.forEach(res => {
                        if (res && res.data) {
                            let row = frm.add_child('itens');
                            row.sales_order = res.so_name;
                            row.customer = res.data.customer;
                            row.customer_name = res.data.customer_name;
                            row.valor_pedido = res.data.valor_pedido;
                            row.peso_liquido = res.data.peso_liquido;
                            row.peso_bruto = res.data.peso_bruto;
                            row.volumes = res.data.volumes || 1;
                            row.faturar = 1;
                            row.status_faturamento = 'Pendente';
                        }
                    });
                    frm.refresh_field('itens');
                    frm.trigger('recalcular_totais');
                    frm.save();
                }).catch(() => frappe.dom.unfreeze());
            }
        });
    },

    executar_faturamento_carga: function(frm) {
        let selecionados = (frm.doc.itens || []).filter(r => r.faturar && r.status_faturamento !== 'Faturado');
        if (selecionados.length === 0) {
            frappe.msgprint(__('Nenhum pedido pendente selecionado para faturamento.'));
            return;
        }

        frappe.confirm(
            __('Confirma o faturamento e a emissão de NF-e para os {0} pedidos selecionados?', [selecionados.length]),
            function() {
                frappe.dom.freeze(__('Faturando pedidos e emitindo Notas Fiscais na SEFAZ...'));
                frm.call({
                    method: 'faturar_carga',
                    doc: frm.doc,
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        frm.reload_doc();
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Resultado do Faturamento da Carga'),
                                indicator: r.message.success ? 'green' : 'orange',
                                message: r.message.message
                            });
                        }
                    }
                });
            }
        );
    },

    recalcular_totais: function(frm) {
        let tot_ped = 0, tot_vol = 0.0, tot_pl = 0.0, tot_pb = 0.0, tot_vl = 0.0;
        (frm.doc.itens || []).forEach(r => {
            tot_ped += 1;
            tot_vol += flt(r.volumes);
            tot_pl += flt(r.peso_liquido);
            tot_pb += flt(r.peso_bruto);
            tot_vl += flt(r.valor_pedido);
        });
        frm.set_value('total_pedidos', tot_ped);
        frm.set_value('total_volumes', tot_vol);
        frm.set_value('total_peso_liquido', tot_pl);
        frm.set_value('total_peso_bruto', tot_pb);
        frm.set_value('valor_total_carga', tot_vl);
    }
});

frappe.ui.form.on('Montagem de Carga Item', {
    volumes: (frm) => frm.trigger('recalcular_totais'),
    peso_liquido: (frm) => frm.trigger('recalcular_totais'),
    peso_bruto: (frm) => frm.trigger('recalcular_totais'),
    itens_remove: (frm) => frm.trigger('recalcular_totais')
});
