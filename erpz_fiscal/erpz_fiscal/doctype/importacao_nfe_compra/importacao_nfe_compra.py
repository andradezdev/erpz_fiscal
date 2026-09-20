import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, now_datetime
from lxml import etree
import re

class ImportacaoNFeCompra(Document):
    def validate(self):
        if self.arquivo_xml and (not self.chave_acesso or not self.itens):
            self.processar_xml()

    @frappe.whitelist()
    def processar_xml(self):
        xml_content = None
        if self.xml_completo:
            xml_content = self.xml_completo
        elif self.arquivo_xml:
            file_name = frappe.db.get_value("File", {"file_url": self.arquivo_xml}, "name")
            if file_name:
                file_doc = frappe.get_doc("File", file_name)
                xml_content = file_doc.get_content()
            else:
                import os
                full_path = frappe.get_site_path(self.arquivo_xml.lstrip("/"))
                if os.path.exists(full_path):
                    with open(full_path, "rb") as f:
                        xml_content = f.read()

        if not xml_content:
            frappe.throw(_("Não foi possível carregar o conteúdo do arquivo XML."))

        self.xml_completo = xml_content.decode("utf-8", errors="ignore") if isinstance(xml_content, bytes) else str(xml_content)

        root = etree.fromstring(xml_content if isinstance(xml_content, bytes) else xml_content.encode("utf-8"))
        # Remove namespace for easier parsing
        for elem in root.getiterator():
            if not hasattr(elem.tag, "find"):
                continue
            i = elem.tag.find("}")
            if i >= 0:
                elem.tag = elem.tag[i + 1:]

        infNFe = root.find(".//infNFe")
        if infNFe is None:
            frappe.throw(_("Estrutura da NF-e não encontrada no XML."))

        # Chave de Acesso
        id_attr = infNFe.get("Id", "")
        self.chave_acesso = id_attr.replace("NFe", "") if id_attr else ""

        # Identificação (ide)
        ide = root.find(".//ide")
        if ide is not None:
            self.numero_nota = cint(ide.findtext("nNF"))
            self.serie = cint(ide.findtext("serie") or 1)
            dh_emi = ide.findtext("dhEmi") or ide.findtext("dEmi")
            self.data_emissao = dh_emi[:19].replace("T", " ") if dh_emi else now_datetime()

        # Emitente (Fornecedor)
        emit = root.find(".//emit")
        if emit is not None:
            cnpj_raw = emit.findtext("CNPJ") or emit.findtext("CPF") or ""
            self.fornecedor_cnpj = cnpj_raw
            self.fornecedor_nome = emit.findtext("xNome") or "Fornecedor"
            self.fornecedor_ie = emit.findtext("IE") or ""
            ender = emit.find(".//enderEmit")
            if ender is not None:
                self.fornecedor_uf = ender.findtext("UF") or ""

            # Localiza ou cadastra o Supplier no ERPNext
            self.vincular_ou_criar_fornecedor(cnpj_raw, self.fornecedor_nome, self.fornecedor_ie)

        # Totais da Nota
        tot = root.find(".//total/ICMSTot")
        if tot is not None:
            self.valor_produtos = flt(tot.findtext("vProd"))
            self.valor_frete = flt(tot.findtext("vFrete"))
            self.valor_seguro = flt(tot.findtext("vSeg"))
            self.valor_desconto = flt(tot.findtext("vDesc"))
            self.valor_outras_despesas = flt(tot.findtext("vOutro"))
            self.valor_total_nota = flt(tot.findtext("vNF"))
            self.total_icms = flt(tot.findtext("vICMS"))
            self.total_st = flt(tot.findtext("vST"))
            self.total_ipi = flt(tot.findtext("vIPI"))
            self.total_pis = flt(tot.findtext("vPIS"))
            self.total_cofins = flt(tot.findtext("vCOFINS"))

        # Itens (det)
        self.itens = []
        dets = root.findall(".//det")
        deposito_padrao = self.deposito_padrao or frappe.db.get_value("Warehouse", {"company": self.empresa, "is_group": 0}, "name")

        for det in dets:
            prod = det.find(".//prod")
            if prod is None:
                continue

            cprod = prod.findtext("cProd") or ""
            xprod = prod.findtext("xProd") or ""
            ncm = prod.findtext("NCM") or ""
            cfop_orig = prod.findtext("CFOP") or ""
            ucom = prod.findtext("uCom") or "UN"
            qcom = flt(prod.findtext("qCom"))
            vuncom = flt(prod.findtext("vUnCom"))
            vprod = flt(prod.findtext("vProd"))

            # Impostos
            vicms = flt(det.findtext(".//ICMS//vICMS"))
            picms = flt(det.findtext(".//ICMS//pICMS"))
            vst = flt(det.findtext(".//ICMS//vICMSST"))
            vipi = flt(det.findtext(".//IPI//vIPI"))
            vpis = flt(det.findtext(".//PIS//vPIS"))
            vcofins = flt(det.findtext(".//COFINS//vCOFINS"))

            # Busca De-Para cadastrado
            item_code = None
            fator = 1.0
            cfop_ent = None

            if self.supplier:
                map_name = frappe.db.get_value("Mapeamento Item Fornecedor", {"supplier": self.supplier, "codigo_fornecedor": cprod}, "name")
                if map_name:
                    m = frappe.get_doc("Mapeamento Item Fornecedor", map_name)
                    item_code = m.item_code
                    fator = flt(m.fator_conversao or 1.0)
                    cfop_ent = m.cfop_padrao_entrada

            # Se não houver CFOP mapeado, sugere pela operação
            if not cfop_ent:
                is_inter = (self.fornecedor_uf and self.fornecedor_uf != "SP")
                if "Industrialização" in (self.tipo_operacao_padrao or ""):
                    cfop_ent = "2101" if is_inter else "1101"
                elif "Uso e Consumo" in (self.tipo_operacao_padrao or ""):
                    cfop_ent = "2556" if is_inter else "1556"
                elif "Ativo" in (self.tipo_operacao_padrao or ""):
                    cfop_ent = "2551" if is_inter else "1551"
                else:
                    cfop_ent = "2102" if is_inter else "1102"

            # Tenta casar item interno pelo código idêntico ou pelo EAN
            if not item_code:
                if frappe.db.exists("Item", cprod):
                    item_code = cprod
                else:
                    ean = prod.findtext("cEAN")
                    if ean and ean != "SEM GTIN":
                        item_code = frappe.db.get_value("Item", {"barcode": ean}, "name")

            qtd_estoque = qcom * fator
            uom_est = frappe.db.get_value("Item", item_code, "stock_uom") if item_code else ucom

            self.append("itens", {
                "codigo_fornecedor": cprod,
                "descricao_fornecedor": xprod,
                "ncm": ncm,
                "cfop_origem": cfop_orig,
                "cfop_entrada": cfop_ent,
                "unidade_fornecedor": ucom,
                "quantidade_fornecedor": qcom,
                "valor_unitario": vuncom,
                "valor_total": vprod,
                "item_code": item_code,
                "fator_conversao": fator,
                "quantidade_estoque": qtd_estoque,
                "unidade_estoque": uom_est,
                "warehouse": deposito_padrao,
                "valor_icms": vicms,
                "aliquota_icms": picms,
                "valor_icms_st": vst,
                "valor_ipi": vipi,
                "valor_pis": vpis,
                "valor_cofins": vcofins
            })

        self.status = "Validada"
        return True

    def vincular_ou_criar_fornecedor(self, cnpj_raw, nome, ie):
        # Limpa pontuação
        cnpj_clean = re.sub(r'\D', '', cnpj_raw)
        if not cnpj_clean:
            return

        # Busca por tax_id ou por nome
        sup_name = frappe.db.get_value("Supplier", {"tax_id": cnpj_clean}, "name")
        if not sup_name and len(cnpj_clean) == 14:
            cnpj_fmt = f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
            sup_name = frappe.db.get_value("Supplier", {"tax_id": cnpj_fmt}, "name")

        if not sup_name:
            # Busca pelo nome
            sup_name = frappe.db.get_value("Supplier", {"supplier_name": nome}, "name")

        if not sup_name:
            # Cria o Supplier
            sup = frappe.new_doc("Supplier")
            sup.supplier_name = nome
            sup.supplier_group = "Local" if frappe.db.exists("Supplier Group", "Local") else "All Supplier Groups"
            sup.supplier_type = "Company"
            sup.country = "Brazil"
            sup.tax_id = cnpj_clean
            sup.insert(ignore_permissions=True)
            sup_name = sup.name

        self.supplier = sup_name

    @frappe.whitelist()
    def salvar_mapeamentos_itens(self):
        """Grava o De-Para de todos os itens associados para automatizar próximas compras"""
        if not self.supplier:
            frappe.throw(_("Fornecedor não identificado para gravar mapeamentos."))

        saved_count = 0
        for it in self.itens:
            if it.item_code:
                map_name = f"MAP-{self.supplier}-{it.codigo_fornecedor}"
                if frappe.db.exists("Mapeamento Item Fornecedor", map_name):
                    doc_map = frappe.get_doc("Mapeamento Item Fornecedor", map_name)
                    doc_map.item_code = it.item_code
                    doc_map.fator_conversao = flt(it.fator_conversao or 1.0)
                    doc_map.cfop_padrao_entrada = it.cfop_entrada
                    doc_map.uom_fornecedor = it.unidade_fornecedor
                    doc_map.save(ignore_permissions=True)
                else:
                    doc_map = frappe.new_doc("Mapeamento Item Fornecedor")
                    doc_map.name = map_name
                    doc_map.supplier = self.supplier
                    doc_map.codigo_fornecedor = it.codigo_fornecedor
                    doc_map.descricao_fornecedor = it.descricao_fornecedor
                    doc_map.uom_fornecedor = it.unidade_fornecedor
                    doc_map.item_code = it.item_code
                    doc_map.fator_conversao = flt(it.fator_conversao or 1.0)
                    doc_map.cfop_padrao_entrada = it.cfop_entrada
                    doc_map.insert(ignore_permissions=True)
                saved_count += 1

        frappe.db.commit()
        return {"success": True, "saved_count": saved_count}

    @frappe.whitelist()
    def gerar_purchase_receipt(self):
        """Gera o Recebimento Físico no Estoque (Purchase Receipt)"""
        if self.purchase_receipt:
            frappe.throw(_("Entrada de Estoque já gerada: {0}").format(self.purchase_receipt))

        self.validar_itens_mapeados()

        pr = frappe.new_doc("Purchase Receipt")
        pr.supplier = self.supplier
        pr.company = self.empresa
        pr.posting_date = nowdate()
        pr.set_warehouse = self.deposito_padrao

        for it in self.itens:
            qtd = flt(it.quantidade_estoque) or (flt(it.quantidade_fornecedor) * flt(it.fator_conversao or 1.0))
            taxa = flt(it.valor_total) / qtd if qtd > 0 else flt(it.valor_unitario)

            stk_uom = frappe.db.get_value("Item", it.item_code, "stock_uom")
            target_uom = it.unidade_estoque or stk_uom
            item_uoms = [u.uom for u in frappe.get_doc("Item", it.item_code).uoms] if frappe.db.exists("Item", it.item_code) else []
            if target_uom != stk_uom and target_uom not in item_uoms:
                target_uom = stk_uom

            pr.append("items", {
                "item_code": it.item_code,
                "qty": qtd,
                "uom": target_uom,
                "stock_uom": stk_uom,
                "rate": taxa,
                "warehouse": it.warehouse or self.deposito_padrao
            })

        pr.insert(ignore_permissions=True)
        pr.submit()

        self.purchase_receipt = pr.name
        self.status = "Concluída" if self.purchase_invoice else "Estoque Recebido"
        self.save(ignore_permissions=True)
        self.salvar_mapeamentos_itens()
        frappe.db.commit()

        return {"success": True, "purchase_receipt": pr.name}

    @frappe.whitelist()
    def gerar_purchase_invoice(self):
        """Gera a Fatura de Compra com Contas a Pagar (Purchase Invoice)"""
        if self.purchase_invoice:
            frappe.throw(_("Fatura de Compra já gerada: {0}").format(self.purchase_invoice))

        self.validar_itens_mapeados()

        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = self.supplier
        pi.company = self.empresa
        pi.bill_no = str(self.numero_nota)
        pi.bill_date = getdate(self.data_emissao)
        pi.posting_date = nowdate()
        pi.set_warehouse = self.deposito_padrao

        for it in self.itens:
            qtd = flt(it.quantidade_estoque) or (flt(it.quantidade_fornecedor) * flt(it.fator_conversao or 1.0))
            taxa = flt(it.valor_total) / qtd if qtd > 0 else flt(it.valor_unitario)

            stk_uom = frappe.db.get_value("Item", it.item_code, "stock_uom")
            target_uom = it.unidade_estoque or stk_uom
            item_uoms = [u.uom for u in frappe.get_doc("Item", it.item_code).uoms] if frappe.db.exists("Item", it.item_code) else []
            if target_uom != stk_uom and target_uom not in item_uoms:
                target_uom = stk_uom

            pi.append("items", {
                "item_code": it.item_code,
                "qty": qtd,
                "uom": target_uom,
                "stock_uom": stk_uom,
                "rate": taxa,
                "warehouse": it.warehouse or self.deposito_padrao
            })

        pi.insert(ignore_permissions=True)
        pi.submit()

        self.purchase_invoice = pi.name
        self.status = "Concluída" if self.purchase_receipt else "Faturada"
        self.save(ignore_permissions=True)
        self.salvar_mapeamentos_itens()
        frappe.db.commit()

        return {"success": True, "purchase_invoice": pi.name}

    @frappe.whitelist()
    def gerar_ambos(self):
        """Gera a Entrada de Estoque e a Fatura de Compra simultaneamente"""
        res_pr = self.gerar_purchase_receipt()
        res_pi = self.gerar_purchase_invoice()
        return {
            "success": True,
            "purchase_receipt": res_pr.get("purchase_receipt"),
            "purchase_invoice": res_pi.get("purchase_invoice")
        }

    def validar_itens_mapeados(self):
        nao_mapeados = [it.descricao_fornecedor for it in self.itens if not it.item_code]
        if nao_mapeados:
            frappe.throw(_("Existem itens no XML sem correspondência com o cadastro interno do ERPNext:<br><b>{0}</b><br>Por favor selecione o Item Interno correspondente na tabela de itens antes de gerar os documentos.").format("<br>• ".join(nao_mapeados)))
