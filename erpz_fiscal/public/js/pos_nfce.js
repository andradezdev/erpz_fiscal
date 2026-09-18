// ERPZ Fiscal - Integracao Oficial e Independente com o Ponto de Venda (PDV)
// Funciona em qualquer site Frappe/ERPNext sem modificar os arquivos nativos do ERPNext

function init_erpz_fiscal_pos() {
    if (!window.erpnext || !erpnext.PointOfSale || !erpnext.PointOfSale.Controller) {
        setTimeout(init_erpz_fiscal_pos, 300);
        return;
    }

    if (erpnext.PointOfSale.Controller.prototype._erpz_fiscal_patched) return;
    erpnext.PointOfSale.Controller.prototype._erpz_fiscal_patched = true;

    // 1. Injeta o botao 'Imprimir Ultimo Cupom NFC-e' no cabecalho do PDV
    const orig_prepare_btns = erpnext.PointOfSale.Controller.prototype.prepare_btns;
    erpnext.PointOfSale.Controller.prototype.prepare_btns = function() {
        orig_prepare_btns.call(this);
        const me = this;
        this.page.add_inner_button(__("Imprimir Último Cupom NFC-e"), () => {
            frappe.db.get_list("POS Invoice", {
                filters: { docstatus: 1 },
                order_by: "creation desc",
                limit: 1,
                fields: ["name", "status_fiscal"]
            }).then(records => {
                if (records && records.length > 0) {
                    window.open("/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=" + encodeURIComponent(records[0].name));
                } else {
                    frappe.msgprint(__("Nenhuma venda recente encontrada no PDV."));
                }
            });
        });
    };

    // 2. Intercepta o evento submit_invoice para perguntar se deseja emitir NFC-e
    const orig_init_payments = erpnext.PointOfSale.Controller.prototype.init_payments;
    erpnext.PointOfSale.Controller.prototype.init_payments = function() {
        orig_init_payments.call(this);
        const me = this;

        if (me.payment && me.payment.events) {
            me.payment.events.submit_invoice = () => {
                const dialog = new frappe.ui.Dialog({
                    title: __("Emissão de Documento Fiscal (NFC-e)"),
                    fields: [
                        {
                            fieldtype: "HTML",
                            fieldname: "info_html",
                            options: `
                                <div class="p-2 text-center">
                                    <h5 style="color: #1e293b; font-weight: bold; margin-bottom: 6px;">Deseja emitir o Cupom Fiscal (NFC-e)?</h5>
                                    <p class="text-muted small mb-3">Escolha se esta venda deve gerar o Cupom NFC-e na SEFAZ ou apenas ser registrada internamente.</p>
                                </div>
                            `
                        },
                        {
                            fieldtype: "Data",
                            fieldname: "cpf_cnpj",
                            label: __("CPF / CNPJ do Consumidor (Opcional)"),
                            description: __("Deixe em branco para Consumidor Final não identificado")
                        }
                    ],
                    primary_action_label: __("Sim, Emitir NFC-e"),
                    primary_action: (values) => {
                        dialog.hide();

                        if (values && values.cpf_cnpj && me.frm.doc) {
                            me.frm.doc.tax_id = values.cpf_cnpj;
                        }

                        // Submete diretamente sem o confirm redundante do Frappe
                        me.frm.doc.__skip_submit_confirm = true;
                        me.frm.save("Submit").then(() => {
                            const inv_name = me.frm.doc.name;
                            me.toggle_components(false);
                            me.toggle_submitted_invoice_summary(true);

                            frappe.dom.freeze(__("Emitindo NFC-e e gerando cupom..."));
                            frappe.call({
                                method: "erpz_fiscal.api.nfe.emitir_nfce_pos_invoice",
                                args: { pos_invoice: inv_name },
                                callback: function(res) {
                                    frappe.dom.unfreeze();
                                    if (res.message && res.message.success) {
                                        frappe.show_alert({
                                            indicator: "green",
                                            message: __("NFC-e Nº {0} Autorizada com Sucesso!", [res.message.numero_nfe])
                                        });
                                        window.open("/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=" + encodeURIComponent(inv_name));
                                    } else {
                                        let msg = res.message ? res.message.mensagem : "Erro na transmissão";
                                        frappe.msgprint({
                                            title: __("Retorno da SEFAZ: NFC-e Rejeitada"),
                                            indicator: "red",
                                            message: msg
                                        });
                                    }
                                },
                                error: function() {
                                    frappe.dom.unfreeze();
                                }
                            });
                        }).catch((err) => {
                            frappe.dom.unfreeze();
                            console.error(err);
                        });
                    },
                    secondary_action_label: __("Não, Venda Sem Cupom"),
                    secondary_action: () => {
                        dialog.hide();
                        me.frm.doc.__skip_submit_confirm = true;
                        me.frm.save("Submit").then(() => {
                            const inv_name = me.frm.doc.name;
                            me.toggle_components(false);
                            me.toggle_submitted_invoice_summary(true);
                            frappe.show_alert({
                                indicator: "green",
                                message: __("Venda {0} registrada com sucesso (Sem NFC-e)", [inv_name]),
                            });
                        }).catch((err) => {
                            frappe.dom.unfreeze();
                            console.error(err);
                        });
                    }
                });
                dialog.show();
            };
        }
    };

    // 3. Injeta o botao verde de impressao do cupom no resumo de pedidos (PastOrderSummary)
    if (erpnext.PointOfSale.PastOrderSummary) {
        const orig_add_summary_btns = erpnext.PointOfSale.PastOrderSummary.prototype.add_summary_btns;
        erpnext.PointOfSale.PastOrderSummary.prototype.add_summary_btns = function(map) {
            orig_add_summary_btns.call(this, map);
            const self = this;

            if (this.$summary_btns.find(".print-nfce-btn").length === 0) {
                const btn = $(`
                    <div class="summary-btn btn btn-primary print-nfce-btn mr-2" style="background:#16a34a !important; border-color:#15803d !important; color:#fff !important; font-weight:bold; cursor:pointer;">
                        <i class="octicon octicon-file-text mr-1"></i> ${__("Imprimir Cupom NFC-e (80mm)")}
                    </div>
                `);
                btn.on("click", function() {
                    if (self.doc && self.doc.name) {
                        window.open("/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=" + encodeURIComponent(self.doc.name));
                    }
                });
                this.$summary_btns.prepend(btn);
            }
        };
    }
}

// Inicializa quando a pagina point-of-sale carrega
$(document).on("page-change", function() {
    if (frappe.get_route_str() === "point-of-sale") {
        init_erpz_fiscal_pos();
    }
});

$(document).ready(function() {
    if (window.frappe && frappe.get_route_str && frappe.get_route_str() === "point-of-sale") {
        init_erpz_fiscal_pos();
    }
});
