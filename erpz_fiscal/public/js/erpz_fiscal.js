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

function print_last_nfce_cupom() {
    frappe.db.get_list('POS Invoice', {
        filters: { docstatus: 1 },
        order_by: 'creation desc',
        limit: 1,
        fields: ['name', 'numero_nfe', 'status_fiscal']
    }).then(records => {
        if (records && records.length > 0) {
            window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(records[0].name));
        } else {
            frappe.msgprint(__('Nenhuma venda encontrada no PDV.'));
        }
    });
}

function ensure_nfce_pos_buttons() {
    if (!window.frappe || !frappe.get_route_str) return;
    if (frappe.get_route_str() !== "point-of-sale") return;

    // 1. Injeta o botão verde diretamente antes do botão "Recent Orders"
    const $recent_btn = $('button:contains("Recent Orders"), button:contains("Pedidos Recentes")');
    if ($recent_btn.length > 0 && $(".btn-nfce-top-bar").length === 0) {
        const $btn = $(`
            <button class="btn btn-default btn-sm btn-nfce-top-bar mr-2" style="background-color: #16a34a !important; color: #ffffff !important; border-color: #15803d !important; font-weight: bold; cursor: pointer; display: inline-flex; align-items: center;">
                <i class="octicon octicon-file-text mr-1"></i> Imprimir Cupom NFC-e (80mm)
            </button>
        `);
        $btn.on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            print_last_nfce_cupom();
        });
        $recent_btn.before($btn);
    }

    // 2. Injeta botão no resumo da venda (quando aberto na lateral ou em Recent Orders)
    const $summary_btns = $(".past-order-summary .summary-btns");
    if ($summary_btns.length > 0 && $summary_btns.is(":visible") && $summary_btns.find(".btn-nfce-summary").length === 0) {
        const $btn_sum = $(`
            <div class="summary-btn btn btn-primary btn-nfce-summary mr-2" style="background-color: #16a34a !important; border-color: #15803d !important; color: #ffffff !important; font-weight: bold; cursor: pointer;">
                <i class="octicon octicon-file-text mr-1"></i> Imprimir Cupom NFC-e (80mm)
            </div>
        `);
        $btn_sum.on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            let inv_name = null;
            if (window.cur_pos && cur_pos.order_summary && cur_pos.order_summary.doc) {
                inv_name = cur_pos.order_summary.doc.name;
            } else {
                inv_name = $(".past-order-summary .invoice-name").text().trim();
            }
            if (inv_name) {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(inv_name));
            } else {
                print_last_nfce_cupom();
            }
        });
        $summary_btns.prepend($btn_sum);
    }

    // 3. Adiciona item no menu (...) caso não exista
    const $menu = $(".page-actions .menu-btn-group .dropdown-menu");
    if ($menu.length > 0 && $menu.find(".menu-nfce-print").length === 0) {
        const $item = $(`
            <li>
                <a class="dropdown-item menu-nfce-print" href="#" style="font-weight: 600; color: #16a34a;">
                    <i class="octicon octicon-file-text mr-2"></i> Imprimir Último Cupom NFC-e
                </a>
            </li>
        `);
        $item.on("click", function(e) {
            e.preventDefault();
            print_last_nfce_cupom();
        });
        $menu.prepend($item);
    }
}

// Observador contínuo na tela do PDV a cada 300ms
setInterval(ensure_nfce_pos_buttons, 300);

$(document).on("page-change", function() {
    setTimeout(ensure_nfce_pos_buttons, 200);
});
