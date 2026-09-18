frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (frm.doc.status_fiscal === 'Autorizada' || frm.doc.documento_fiscal) {
            frm.add_custom_button(__('Imprimir DANFE (PDF)'), function() {
                window.open('/api/method/erpz_fiscal.api.nfe.imprimir_danfe?sales_invoice=' + encodeURIComponent(frm.doc.name));
            }, __('Ações Fiscais')).addClass('btn-primary');

            frm.add_custom_button(__('Ver Documento Fiscal'), function() {
                frappe.set_route('Form', 'Documento Fiscal Eletronico', frm.doc.documento_fiscal);
            }, __('Ações Fiscais'));
        }
    }
});
