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
