// Sincronização automática do layout de desktop para garantir que novos módulos apareçam
function ensure_desktop_layout_sync() {
    try {
        const user = (window.frappe && frappe.session && frappe.session.user) ? frappe.session.user : "Administrator";
        const key = user + ":desktop";
        const raw = localStorage.getItem(key);
        if (raw) {
            let layout = JSON.parse(raw);
            if (Array.isArray(layout)) {
                const hasContabil = layout.some(i => (i.label === "ERPZ Contabil" || i.name === "ERPZ Contabil"));
                if (!hasContabil) {
                    console.log("[ERPZ] Atualizando layout do Desk em localStorage para incluir ERPZ Contabil...");
                    const contabilItem = {
                        label: "ERPZ Contabil",
                        bg_color: "gray",
                        link: null,
                        link_type: "Workspace Sidebar",
                        app: "erpz_contabil",
                        icon_type: "Link",
                        parent_icon: "",
                        icon: "calculator",
                        link_to: "ERPZ Contabil",
                        idx: 10,
                        standard: 1,
                        logo_url: null,
                        hidden: 0,
                        name: "ERPZ Contabil",
                        restrict_removal: 0,
                        icon_image: null
                    };
                    const idxT = layout.findIndex(i => (i.label === "ERPZ Transporte" || i.name === "ERPZ Transporte"));
                    if (idxT !== -1) {
                        layout.splice(idxT + 1, 0, contabilItem);
                    } else {
                        layout.push(contabilItem);
                    }
                    localStorage.setItem(key, JSON.stringify(layout));
                    if (window.frappe && frappe.desktop_icons && Array.isArray(frappe.desktop_icons)) {
                        frappe.desktop_icons = layout;
                    }
                    if (window.frappe && frappe.pages && frappe.pages["desktop"] && frappe.pages["desktop"].desktop_page) {
                        frappe.pages["desktop"].desktop_page.data = null;
                        frappe.pages["desktop"].desktop_page.update();
                    }

                const hasCargoNext = layout.some(i => (i.label === "CargoNext" || i.name === "CargoNext"));
                if (!hasCargoNext) {
                    console.log("[ERPZ] Atualizando layout do Desk em localStorage para incluir CargoNext...");
                    const cargoNextItem = {
                        label: "CargoNext",
                        bg_color: "blue",
                        link: null,
                        link_type: "Workspace Sidebar",
                        app: "logistics",
                        icon_type: "Link",
                        parent_icon: "",
                        icon: "package",
                        link_to: "CargoNext",
                        idx: 13,
                        standard: 1,
                        logo_url: null,
                        hidden: 0,
                        name: "CargoNext",
                        restrict_removal: 0,
                        icon_image: null
                    };
                    const idxF = layout.findIndex(i => (i.label === "ERPZ Financeiro" || i.name === "ERPZ Financeiro"));
                    if (idxF !== -1) {
                        layout.splice(idxF + 1, 0, cargoNextItem);
                    } else {
                        layout.push(cargoNextItem);
                    }
                    localStorage.setItem(key, JSON.stringify(layout));
                    if (window.frappe && frappe.desktop_icons && Array.isArray(frappe.desktop_icons)) {
                        frappe.desktop_icons = layout;
                    }
                    if (window.frappe && frappe.pages && frappe.pages["desktop"] && frappe.pages["desktop"].desktop_page) {
                        frappe.pages["desktop"].desktop_page.data = null;
                        frappe.pages["desktop"].desktop_page.update();
                    }
                }

                const hasEd = layout.some(i => (i.label === "ERPZ Educacional" || i.name === "ERPZ Educacional"));
                if (!hasEd) {
                    console.log("[ERPZ] Atualizando layout do Desk em localStorage para incluir ERPZ Educacional...");
                    const edItem = {
                        label: "ERPZ Educacional",
                        bg_color: "blue",
                        link: null,
                        link_type: "Workspace Sidebar",
                        app: "ifitwala_ed",
                        icon_type: "Link",
                        parent_icon: "",
                        icon: "education",
                        link_to: "ERPZ Educacional",
                        idx: 14,
                        standard: 1,
                        logo_url: null,
                        hidden: 0,
                        name: "ERPZ Educacional",
                        restrict_removal: 0,
                        icon_image: null
                    };
                    layout.push(edItem);
                    localStorage.setItem(key, JSON.stringify(layout));
                    if (window.frappe && frappe.desktop_icons && Array.isArray(frappe.desktop_icons)) {
                        frappe.desktop_icons = layout;
                    }
                    if (window.frappe && frappe.pages && frappe.pages["desktop"] && frappe.pages["desktop"].desktop_page) {
                        frappe.pages["desktop"].desktop_page.data = null;
                        frappe.pages["desktop"].desktop_page.update();
                    }
                }
                }
            }
        }
    } catch(e) {
        console.warn("[ERPZ] sync layout warning:", e);
    }
}

$(document).on("toolbar_setup", function() {
    ensure_desktop_layout_sync();
});

$(document).on("page-change", function() {
    ensure_desktop_layout_sync();
    setTimeout(ensure_nfce_pos_buttons, 200);
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
