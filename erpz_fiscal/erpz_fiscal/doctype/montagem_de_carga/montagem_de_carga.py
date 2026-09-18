import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

class MontagemdeCarga(Document):
    def validate(self):
        if not self.empresa:
            self.empresa = frappe.defaults.get_user_default("Company")
        self.calcular_totais()

    def calcular_totais(self):
        tot_pedidos = 0
        tot_volumes = 0.0
        tot_peso_liq = 0.0
        tot_peso_bruto = 0.0
        tot_valor = 0.0

        for item in (self.itens or []):
            tot_pedidos += 1
            tot_volumes += flt(item.get("volumes"))
            tot_peso_liq += flt(item.get("peso_liquido"))
            tot_peso_bruto += flt(item.get("peso_bruto"))
            tot_valor += flt(item.get("valor_pedido"))

        self.total_pedidos = tot_pedidos
        self.total_volumes = tot_volumes
        self.total_peso_liquido = tot_peso_liq
        self.total_peso_bruto = tot_peso_bruto
        self.valor_total_carga = tot_valor

    @frappe.whitelist()
    def faturar_carga(self):
        if not self.itens:
            frappe.throw(_("Não há pedidos na carga para faturar."))

        itens_a_faturar = [row for row in self.itens if row.faturar and row.status_faturamento != "Faturado"]
        if not itens_a_faturar:
            frappe.msgprint(_("Todos os pedidos selecionados nesta carga já se encontram faturados com NF-e."))
            return {"success": True, "processados": 0, "erros": 0, "message": _("Todos os pedidos selecionados já estão faturados.")}

        processados = 0
        erros = 0
        notas_autorizadas = []
        mensagens_erro = []

        for row in itens_a_faturar:
            try:
                so_doc = frappe.get_doc("Sales Order", row.sales_order)
                inv_name = row.sales_invoice

                # 1. Verifica se o pedido já foi faturado anteriormente (ex: via faturamento individual)
                existing_inv = inv_name or so_doc.get("sales_invoice") or frappe.db.get_value(
                    "Sales Invoice Item", {"sales_order": row.sales_order, "docstatus": 1}, "parent"
                )

                if existing_inv:
                    inv_doc = frappe.get_doc("Sales Invoice", existing_inv)
                    dfe_name = inv_doc.get("documento_fiscal") or so_doc.get("documento_fiscal") or frappe.db.get_value(
                        "Documento Fiscal Eletronico", {"voucher_no": existing_inv}, "name"
                    )

                    if dfe_name:
                        dfe = frappe.get_doc("Documento Fiscal Eletronico", dfe_name)
                        row.sales_invoice = existing_inv
                        row.documento_fiscal = dfe.name
                        row.numero_nfe = str(dfe.numero_nota)
                        row.chave_nfe = dfe.chave_acesso
                        row.status_faturamento = "Faturado"
                        row.mensagem_retorno = dfe.mensagem_sefaz or _("NF-e Autorizada")
                        notas_autorizadas.append(f"Pedido {row.sales_order}: NF-e {dfe.numero_nota}")
                        processados += 1
                        continue
                    else:
                        inv_name = existing_inv

                # 2. Cria a Sales Invoice se não existir
                if not inv_name:
                    inv = make_sales_invoice(row.sales_order)

                    # Se o pedido já tiver sido faturado e make_sales_invoice vier sem itens
                    if not inv.items:
                        # Tenta buscar fatura anterior submetida
                        prev_inv = frappe.db.get_value("Sales Invoice Item", {"sales_order": row.sales_order, "docstatus": 1}, "parent")
                        if prev_inv:
                            row.sales_invoice = prev_inv
                            inv_name = prev_inv
                        else:
                            row.status_faturamento = "Erro"
                            row.mensagem_retorno = _("Pedido sem itens pendentes de faturamento.")
                            erros += 1
                            mensagens_erro.append(f"Pedido {row.sales_order}: Sem itens pendentes de faturamento")
                            continue
                    else:
                        inv.posting_date = self.data_carga or nowdate()
                        inv.volumes = flt(row.volumes or 1)
                        inv.peso_liquido = flt(row.peso_liquido or 0)
                        inv.peso_bruto = flt(row.peso_bruto or 0)
                        inv.insert(ignore_permissions=True)
                        inv.submit()
                        inv_name = inv.name
                        row.sales_invoice = inv_name

                # 3. Cria e emite o Documento Fiscal Eletronico
                dfe = frappe.new_doc("Documento Fiscal Eletronico")
                dfe.modelo_fiscal = "55 - NF-e"
                dfe.empresa = self.empresa
                dfe.voucher_type = "Sales Invoice"
                dfe.voucher_no = inv_name
                dfe.destinatario_tipo = "Customer"
                dfe.destinatario = so_doc.customer
                dfe.destinatario_nome = row.customer_name or so_doc.customer_name or so_doc.customer
                dfe.transportadora = self.transportadora or ""
                dfe.placa_veiculo = self.placa_veiculo or ""
                dfe.uf_veiculo = self.uf_veiculo or ""
                dfe.quantidade_volumes = row.volumes
                dfe.peso_liquido = row.peso_liquido
                dfe.peso_bruto = row.peso_bruto

                inv_doc = frappe.get_doc("Sales Invoice", inv_name)
                for so_item in inv_doc.items:
                    item_doc = frappe.get_doc("Item", so_item.item_code)
                    dfe.append("itens", {
                        "item_code": so_item.item_code,
                        "descricao": so_item.item_name or item_doc.item_name,
                        "ncm": item_doc.get("ncm") or "00000000",
                        "cfop": "5102",
                        "unidade": so_item.uom or "UN",
                        "quantidade": so_item.qty,
                        "valor_unitario": so_item.rate,
                        "valor_total": so_item.amount,
                        "cst_icms": "00"
                    })

                dfe.aplicar_regras_tributarias()
                dfe.calcular_totais()
                dfe.insert(ignore_permissions=True)

                # Transmite e autoriza
                res = dfe.transmitir_sefaz()
                
                row.documento_fiscal = dfe.name
                row.numero_nfe = str(dfe.numero_nota)
                row.chave_nfe = dfe.chave_acesso
                row.status_faturamento = "Faturado"
                row.mensagem_retorno = dfe.mensagem_sefaz or _("NF-e Autorizada com Sucesso")
                notas_autorizadas.append(f"Pedido {row.sales_order}: NF-e {dfe.numero_nota}")
                processados += 1

            except Exception as e:
                erros += 1
                row.status_faturamento = "Erro"
                err_str = str(e).replace("Data missing in table Itens", "Pedido já faturado anteriormente")
                row.mensagem_retorno = err_str[:250]
                mensagens_erro.append(f"Pedido {row.sales_order}: {err_str[:80]}")
                frappe.log_error(f"Erro ao faturar carga {self.name}: {str(e)}")

        # Verifica status geral da carga
        todos_faturados = all(row.status_faturamento == "Faturado" for row in self.itens if row.faturar)
        if todos_faturados:
            self.status = "Faturada"
        else:
            self.status = "Em Carregamento"

        self.calcular_totais()
        self.save(ignore_permissions=True)
        frappe.db.commit()

        msg = _("Processamento da Carga:<br>&bull; <b>{0} pedidos faturados com NF-e</b><br>&bull; <b>{1} pendentes/erros</b>").format(processados, erros)
        if notas_autorizadas:
            msg += "<br><br><b>Notas Fiscais Autorizadas:</b><br>" + "<br>".join(notas_autorizadas)
        if mensagens_erro:
            msg += "<br><br><span style='color:red;'><b>Avisos/Erros:</b></span><br>" + "<br>".join(mensagens_erro)

        return {"success": erros == 0, "message": msg, "processados": processados, "erros": erros}

@frappe.whitelist()
def calcular_pesos_pedido(sales_order):
    if not sales_order:
        return {}
    so = frappe.get_doc("Sales Order", sales_order)
    tot_liq = sum(flt(item.qty) * flt(frappe.db.get_value("Item", item.item_code, "peso_liquido") or 0) for item in so.items)
    tot_bruto = sum(flt(item.qty) * flt(frappe.db.get_value("Item", item.item_code, "peso_bruto") or 0) for item in so.items)
    return {
        "customer": so.customer,
        "customer_name": so.customer_name,
        "valor_pedido": so.grand_total,
        "peso_liquido": tot_liq,
        "peso_bruto": tot_bruto,
        "volumes": flt(so.get("volumes") or 1.0)
    }
