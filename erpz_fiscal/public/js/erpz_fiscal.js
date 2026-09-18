$(document).on("toolbar_setup", function() {
    try {
        if (!localStorage.getItem("erpz_desktop_cache_v2")) {
            localStorage.removeItem("Administrator:desktop");
            if (window.frappe && frappe.session && frappe.session.user) {
                localStorage.removeItem(frappe.session.user + ":desktop");
            }
            localStorage.setItem("erpz_desktop_cache_v2", "1");
            if (window.frappe && frappe.pages && frappe.pages["desktop"] && frappe.pages["desktop"].desktop_page) {
                frappe.pages["desktop"].desktop_page.update();
            }
        }
    } catch(e) {}
});

function hook_point_of_sale_nfce() {
    if (!window.cur_pos || !window.cur_pos.order_summary) {
        return;
    }

    if (window.cur_pos._erpz_fiscal_hooked) return;
    window.cur_pos._erpz_fiscal_hooked = true;

    // 1. Botão no topo do PDV: "Imprimir Último Cupom NFC-e"
    if (window.cur_pos.page) {
        window.cur_pos.page.add_inner_button(__('Imprimir Último Cupom NFC-e'), function() {
            frappe.db.get_list('POS Invoice', {
                filters: { docstatus: 1, status_fiscal: 'Autorizada' },
                order_by: 'creation desc',
                limit: 1,
                fields: ['name', 'numero_nfe']
            }).then(records => {
                if (records && records.length > 0) {
                    window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(records[0].name));
                } else {
                    frappe.msgprint(__('Nenhum cupom NFC-e autorizado encontrado recentemente.'));
                }
            });
        });
    }

    // 2. Injeta botão no resumo da venda (PastOrderSummary) e abre diálogo automático
    const summary = window.cur_pos.order_summary;
    const orig_load = summary.load_summary_of;
    summary.load_summary_of = function(doc, after_submission = false) {
        orig_load.call(this, doc, after_submission);
        const self = this;

        setTimeout(() => {
            if (!self.$summary_btns) return;

            self.$summary_btns.find(".nfce-btn").remove();

            const btn = $(`
                <button class="btn btn-primary nfce-btn mr-2" style="background-color: #16a34a !important; border-color: #15803d !important; color: #ffffff !important; font-weight: bold; font-size: 13px; padding: 6px 14px; cursor: pointer;">
                    <i class="octicon octicon-file-text mr-1"></i> Imprimir Cupom NFC-e (80mm)
                </button>
            `);

            btn.on("click", function() {
                const inv = self.doc || doc;
                if (inv && inv.name) {
                    window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(inv.name));
                }
            });

            self.$summary_btns.prepend(btn);

            if (after_submission) {
                let d = new frappe.ui.Dialog({
                    title: __('Venda Finalizada - NFC-e Gerada!'),
                    indicator: 'green',
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'html_desc',
                            options: `
                                <div style="text-align: center; padding: 15px;">
                                    <div style="font-size: 38px; color: #16a34a; margin-bottom: 10px;">
                                        <i class="octicon octicon-check-circle"></i>
                                    </div>
                                    <h4 style="color: #1e293b; font-weight: bold; margin-bottom: 6px;">NFC-e Autorizada com Sucesso!</h4>
                                    <p class="text-muted" style="font-size: 13px; margin-bottom: 12px;">Venda: <b>${doc.name}</b></p>
                                    <p style="font-size: 12px; color: #64748b;">Clique abaixo para imprimir o Cupom Fiscal Térmico de 80mm com QR Code oficial da SEFAZ.</p>
                                </div>
                            `
                        }
                    ],
                    primary_action_label: __('Imprimir Cupom NFC-e (80mm)'),
                    primary_action: function() {
                        d.hide();
                        window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(doc.name));
                    },
                    secondary_action_label: __('Nova Venda (Fechar)'),
                    secondary_action: function() {
                        d.hide();
                    }
                });
                d.show();
            }
        }, 200);
    };
}

setInterval(() => {
    if (window.frappe && frappe.get_route_str && frappe.get_route_str() === "point-of-sale") {
        hook_point_of_sale_nfce();
    }
}, 500);
