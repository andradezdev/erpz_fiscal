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
            cellHeight: 34,
            showTotalRow: true
        });
    },

    "onload": function(report) {
        frappe.dom.set_style(`
            /* Tabela Padronizada Idêntica ao Contas a Receber */
            .page-container[data-page-route="query-report"] .datatable,
            .datatable {
                border: 1px solid #d1d5db !important;
                border-radius: 4px !important;
            }
            .datatable .dt-cell {
                border-right: 1px solid #e5e7eb !important;
                border-bottom: 1px solid #e5e7eb !important;
            }
            .datatable .dt-cell--header {
                background-color: #f3f4f6 !important;
                border-right: 1px solid #d1d5db !important;
                border-bottom: 2px solid #cbd5e1 !important;
            }
            .datatable .dt-cell--header .dt-cell__content {
                font-weight: 700 !important;
                color: #1f2937 !important;
                font-size: 11px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.3px !important;
            }
            .datatable .dt-row:nth-child(even) .dt-cell {
                background-color: #f9fafb !important;
            }
            .datatable .dt-row:hover .dt-cell {
                background-color: #f3f4f6 !important;
            }
            .datatable .dt-row.dt-row-total .dt-cell {
                background-color: #f3f4f6 !important;
                font-weight: bold !important;
                border-top: 2px solid #cbd5e1 !important;
            }
        `);
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (column.fieldname === "codigo_status_sefaz") {
            if (data.codigo_status_sefaz === "100" || data.status === "Autorizado") {
                value = `<span class="indicator-pill green" style="font-weight:bold;">100 &bull; Autorizada</span>`;
            } else if (data.codigo_status_sefaz === "105") {
                value = `<span class="indicator-pill orange" style="font-weight:bold;">105 &bull; Processando</span>`;
            } else if (data.codigo_status_sefaz === "101" || data.status === "Cancelado") {
                value = `<span class="indicator-pill gray" style="font-weight:bold;">101 &bull; Cancelada</span>`;
            } else if (data.codigo_status_sefaz) {
                value = `<span class="indicator-pill red" style="font-weight:bold;">${data.codigo_status_sefaz} &bull; Rejeição</span>`;
            } else if (data.name) {
                value = `<span class="indicator-pill gray">Pendente</span>`;
            }
        } else if (column.fieldname === "numero_nota") {
            if (value && data.name) {
                value = `<b>${value}</b>`;
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
