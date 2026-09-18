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

$(document).ready(function() {
    try {
        if (!localStorage.getItem("erpz_desktop_cache_v2")) {
            localStorage.removeItem("Administrator:desktop");
            if (window.frappe && frappe.session && frappe.session.user) {
                localStorage.removeItem(frappe.session.user + ":desktop");
            }
            localStorage.setItem("erpz_desktop_cache_v2", "1");
        }
    } catch(e) {}
});

// Integracao Oficial ERPZ Fiscal com o PDV (NFC-e 80mm)
function setup_pos_nfce_integration() {
    if (!window.erpnext || !erpnext.PointOfSale || !erpnext.PointOfSale.PastOrderSummary) return;
    if (erpnext.PointOfSale.PastOrderSummary._erpz_fiscal_patched) return;
    erpnext.PointOfSale.PastOrderSummary._erpz_fiscal_patched = true;

    const original_load_summary = erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of;
    erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of = function(doc, after_submission = false) {
        original_load_summary.call(this, doc, after_submission);
        
        const me = this;
        setTimeout(() => {
            if (!me.$summary_btns) return;
            
            if (me.$summary_btns.find(".nfce-btn").length === 0) {
                const btn_html = $(`
                    <div class="summary-btn btn btn-primary nfce-btn mr-2" style="background: #16a34a; border-color: #15803d; color: white; font-weight: bold; cursor: pointer;">
                        <i class="octicon octicon-file-text mr-1"></i> Imprimir Cupom NFC-e (80mm)
                    </div>
                `);
                
                btn_html.on("click", function() {
                    const inv_name = me.doc ? me.doc.name : (doc ? doc.name : null);
                    if (inv_name) {
                        window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?pos_invoice=' + encodeURIComponent(inv_name));
                    }
                });
                
                me.$summary_btns.prepend(btn_html);
            }
        }, 150);
    };
}

$(document).on("page-change", function() {
    setTimeout(setup_pos_nfce_integration, 500);
});

$(document).ready(function() {
    setTimeout(setup_pos_nfce_integration, 500);
});
