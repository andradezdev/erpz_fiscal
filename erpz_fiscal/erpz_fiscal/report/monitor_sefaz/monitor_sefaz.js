frappe.query_reports["Monitor SEFAZ"] = {
    "filters": [
        { "fieldname": "empresa", "label": __("Empresa"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company") },
        { "fieldname": "status_filtro", "label": __("Status SEFAZ"), "fieldtype": "Select", "options": "\n100 - Autorizadas\nRejeitadas (Erros)\n105 - Em Processamento\nCanceladas" },
        { "fieldname": "modelo", "label": __("Modelo"), "fieldtype": "Select", "options": "\n55 - NF-e\n65 - NFC-e" },
        { "fieldname": "from_date", "label": __("De"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
        { "fieldname": "to_date", "label": __("Até"), "fieldtype": "Date", "default": frappe.datetime.get_today() }
    ],

    get_datatable_options: function(options) {
        return Object.assign(options, {
            cellHeight: 38,
            inlineFilters: true
        });
    },

    "onload": function(report) {
        frappe.dom.set_style(`
            /* Tabela Profissional Formatada */
            .report-wrapper .dt-scrollable {
                border: 1px solid #cbd5e1 !important;
                border-radius: 6px !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
            }
            .report-wrapper .dt-cell {
                border-right: 1px solid #e2e8f0 !important;
                border-bottom: 1px solid #e2e8f0 !important;
            }
            .report-wrapper .dt-cell--header {
                background-color: #f1f5f9 !important;
                border-bottom: 2px solid #cbd5e1 !important;
            }
            .report-wrapper .dt-cell--header .dt-cell__content {
                font-weight: 700 !important;
                color: #0f172a !important;
                font-size: 11px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.4px !important;
            }
            .report-wrapper .dt-row:nth-child(even) .dt-cell {
                background-color: #f8fafc !important;
            }
            .report-wrapper .dt-row:hover .dt-cell {
                background-color: #f1f5f9 !important;
            }
            .report-summary {
                border-radius: 8px !important;
                border: 1px solid #e2e8f0 !important;
                padding: 12px !important;
                margin-bottom: 16px !important;
                background: #ffffff !important;
            }
        `);
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "codigo_status_sefaz") {
            if (data.codigo_status_sefaz === "100" || data.status === "Autorizado") {
                value = `<span class="badge" style="background:#dcfce7; color:#15803d; font-weight:700; border:1px solid #86efac; padding:3px 8px; border-radius:4px; font-size:11px;">100 &bull; Autorizada</span>`;
            } else if (data.codigo_status_sefaz === "105") {
                value = `<span class="badge" style="background:#fef3c7; color:#b45309; font-weight:700; border:1px solid #fde68a; padding:3px 8px; border-radius:4px; font-size:11px;">105 &bull; Processando</span>`;
            } else if (data.codigo_status_sefaz === "101" || data.status === "Cancelado") {
                value = `<span class="badge" style="background:#f1f5f9; color:#475569; font-weight:700; border:1px solid #cbd5e1; padding:3px 8px; border-radius:4px; font-size:11px;">101 &bull; Cancelada</span>`;
            } else if (data.codigo_status_sefaz) {
                value = `<span class="badge" style="background:#fee2e2; color:#b91c1c; font-weight:700; border:1px solid #fca5a5; padding:3px 8px; border-radius:4px; font-size:11px;">${data.codigo_status_sefaz} &bull; Rejeição</span>`;
            }
        } else if (column.fieldname === "numero_nota") {
            if (value) {
                value = `<strong>${value}</strong>`;
            }
        } else if (column.fieldname === "chave_acesso") {
            if (data.chave_acesso) {
                value = `<span style="font-family: monospace; font-size: 11px; color: #334155;">${data.chave_acesso}</span>`;
            }
        } else if (column.fieldname === "protocolo") {
            if (data.protocolo) {
                value = `<span style="font-family: monospace; font-size: 11px; color: #1e40af; font-weight: 600;">${data.protocolo}</span>`;
            }
        }
        return value;
    }
};
