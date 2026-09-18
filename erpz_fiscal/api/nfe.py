import re
import frappe
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

def validar_cancelamento_fatura(doc, method):
    """Impede o cancelamento de uma fatura com NF-e autorizada sem antes cancelar a NF-e"""
    if doc.get("documento_fiscal"):
        status = frappe.db.get_value("Documento Fiscal Eletronico", doc.documento_fiscal, "status")
        if status == "Autorizado":
            frappe.throw(_("Nºo ? poss?vel cancelar uma fatura com Documento Fiscal Eletrônico autorizado. Cancele o documento fiscal primeiro."))

def calcular_pesos_sales_order(doc, method=None):
    """Calcula automaticamente os pesos bruto e líquido do Pedido de Venda a partir dos itens"""
    if not doc.items:
        return

    tot_pl = 0.0
    tot_pb = 0.0

    for item in doc.items:
        pl = flt(frappe.db.get_value("Item", item.item_code, "peso_liquido") or 0)
        pb = flt(frappe.db.get_value("Item", item.item_code, "peso_bruto") or 0)
        tot_pl += flt(item.qty) * pl
        tot_pb += flt(item.qty) * pb

    doc.peso_liquido = tot_pl
    doc.peso_bruto = tot_pb
    if not flt(doc.volumes):
        doc.volumes = 1.0

@frappe.whitelist()
def faturar_sales_order_individual(sales_order):
    """
    Fatura um Pedido de Venda individualmente na tela da Sales Order e emite a NF-e
    """
    if not sales_order:
        frappe.throw(_("Pedido de Venda n?o informado."))

    so = frappe.get_doc("Sales Order", sales_order)

    if so.docstatus != 1:
        frappe.throw(_("O Pedido de Venda precisa estar submetido para ser faturado."))

    if so.get("status_fiscal") == "Autorizada":
        frappe.throw(_("Este Pedido de Venda j? possui uma Nota Fiscal Eletrônica autorizada: Nº {0}").format(so.numero_nfe))

    # 1. Cria a Sales Invoice
    inv = make_sales_invoice(sales_order)
    inv.posting_date = nowdate()
    inv.volumes = flt(so.volumes or 1)
    inv.peso_liquido = flt(so.peso_liquido or 0)
    inv.peso_bruto = flt(so.peso_bruto or 0)
    inv.insert(ignore_permissions=True)
    inv.submit()

    # 2. Cria o Documento Fiscal Eletrônico desacoplado
    dfe = frappe.new_doc("Documento Fiscal Eletronico")
    dfe.modelo_fiscal = "55 - NF-e"
    dfe.empresa = so.company
    dfe.voucher_type = "Sales Invoice"
    dfe.voucher_no = inv.name
    dfe.destinatario_tipo = "Customer"
    dfe.destinatario = so.customer
    dfe.destinatario_nome = so.customer_name or so.customer
    dfe.quantidade_volumes = inv.volumes
    dfe.peso_liquido = inv.peso_liquido
    dfe.peso_bruto = inv.peso_bruto

    for so_item in inv.items:
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
            "cst_icms": "102"
        })

    dfe.calcular_totais()
    dfe.insert(ignore_permissions=True)

    # 3. Transmite e autoriza na SEFAZ
    res = dfe.transmitir_sefaz()

    # 4. Atualiza o Pedido de Venda
    so.db_set("documento_fiscal", dfe.name)
    so.db_set("numero_nfe", str(dfe.numero_nota))
    so.db_set("chave_nfe", dfe.chave_acesso)
    so.db_set("status_fiscal", "Autorizada" if dfe.status == "Autorizado" else "Pendente")
    frappe.db.commit()

    return {
        "success": True,
        "sales_invoice": inv.name,
        "documento_fiscal": dfe.name,
        "numero_nfe": dfe.numero_nota,
        "chave_nfe": dfe.chave_acesso,
        "status": dfe.status,
        "mensagem": dfe.mensagem_sefaz
    }


@frappe.whitelist()
def imprimir_danfe(documento_fiscal=None, sales_invoice=None, sales_order=None):
    """Gera e faz o download direto do DANFE em PDF"""
    if not documento_fiscal:
        if sales_invoice:
            documento_fiscal = frappe.db.get_value("Sales Invoice", sales_invoice, "documento_fiscal")
        elif sales_order:
            documento_fiscal = frappe.db.get_value("Sales Order", sales_order, "documento_fiscal")

    if not documento_fiscal:
        frappe.throw(_("Documento Fiscal Eletrônico não encontrado para este registro."))

    dfe = frappe.get_doc("Documento Fiscal Eletronico", documento_fiscal)
    from erpz_fiscal.services.danfe import gerar_danfe_pdf
    pdf_bytes = gerar_danfe_pdf(dfe)

    is_nfce = "65" in (dfe.get("modelo_fiscal") or "")
    prefix = "Cupom_NFCe" if is_nfce else "DANFE_NFe"
    frappe.local.response["filename"] = f"{prefix}_{dfe.numero_nota or dfe.name}.pdf"
    frappe.local.response["filecontent"] = pdf_bytes
    frappe.local.response["type"] = "download"


def get_sefaz_client(empresa=None, certificado_name=None):
    from erpbrasil.assinatura.certificado import Certificado
    from erpbrasil.transmissao import TransmissaoSOAP
    from erpbrasil.edoc.nfe import NFe

    if not certificado_name:
        if not empresa:
            empresa = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
        certificado_name = frappe.db.get_value("Certificado Digital", {"empresa": empresa, "status": "Ativo"}, "name")

    if not certificado_name:
        frappe.throw(_("Nenhum Certificado Digital A1 ativo encontrado para a empresa {0}.").format(empresa or ""))

    cert_doc = frappe.get_doc("Certificado Digital", certificado_name)
    file_doc = frappe.get_doc("File", {"file_url": cert_doc.arquivo_pfx})
    pwd = cert_doc.get_password("senha_certificado") or cert_doc.senha_certificado

    cert = Certificado(file_doc.get_full_path(), pwd)
    trans = TransmissaoSOAP(cert, cache=False)
    trans._cache = None

    cfg = frappe.get_doc("Configuracao Fiscal Empresa", cert_doc.empresa) if frappe.db.exists("Configuracao Fiscal Empresa", cert_doc.empresa) else None
    amb = "1" if cfg and "1 - Produção" in (cfg.ambiente or "") else "2"
    amb_label = "1 - Produção" if amb == "1" else "2 - Homologação (Testes)"

    nfe = NFe(transmissao=trans, uf=35, ambiente=amb, mod="55")
    return nfe, amb_label, cert_doc


@frappe.whitelist()
def testar_conexao_sefaz(empresa=None, certificado_name=None):
    """Consulta o status do serviço WebService da SEFAZ SP"""
    try:
        nfe, amb_label, cert_doc = get_sefaz_client(empresa, certificado_name)
        ret = nfe.status_servico()
        resp = getattr(ret, "resposta", None)
        cstat = getattr(resp, "cStat", None) if resp else "Erro"
        xmotivo = getattr(resp, "xMotivo", None) if resp else "Sem resposta da SEFAZ"
        dh = getattr(resp, "dhRecbto", None) if resp else ""

        return {
            "success": True,
            "cStat": cstat,
            "xMotivo": xmotivo,
            "ambiente": amb_label,
            "uf": "SP - São Paulo",
            "dhRecbto": str(dh),
            "empresa": cert_doc.empresa,
            "cnpj": cert_doc.cnpj_certificado
        }
    except Exception as e:
        frappe.log_error(f"Erro ao testar conexão SEFAZ: {str(e)}")
        return {
            "success": False,
            "cStat": "Erro",
            "xMotivo": str(e)
        }


@frappe.whitelist()
def consultar_cadastro_sefaz(empresa=None, cnpj=None, uf="SP"):
    """Consulta a situação cadastral do CNPJ no CADESP / SEFAZ"""
    try:
        nfe, amb_label, cert_doc = get_sefaz_client(empresa)
        target_cnpj = cnpj or cert_doc.cnpj_certificado
        target_cnpj = re.sub(r'\D', '', target_cnpj or '')

        if not target_cnpj:
            frappe.throw(_("CNPJ não informado para consulta cadastral."))

        ret = nfe.consultar_cadastro(uf=uf, cnpj=target_cnpj)
        resp = getattr(ret, "resposta", None)
        infCons = getattr(resp, "infCons", None) if resp else None

        cstat = getattr(infCons, "cStat", None) if infCons else getattr(resp, "cStat", "Erro")
        xmotivo = getattr(infCons, "xMotivo", None) if infCons else getattr(resp, "xMotivo", "Sem resposta da SEFAZ")

        dados_cad = {}
        if infCons and hasattr(infCons, "infCad") and infCons.infCad:
            cad = infCons.infCad[0] if isinstance(infCons.infCad, list) else infCons.infCad
            dados_cad = {
                "IE": getattr(cad, "IE", "Não encontrada"),
                "xNome": getattr(cad, "xNome", ""),
                "cSit": getattr(cad, "cSit", ""),
                "dBaixa": getattr(cad, "dBaixa", ""),
                "xRegApur": getattr(cad, "xRegApur", ""),
                "CNAE": getattr(cad, "CNAE", "")
            }

        return {
            "success": True,
            "cStat": cstat,
            "xMotivo": xmotivo,
            "cnpj": target_cnpj,
            "uf": uf,
            "dados_cadastrais": dados_cad
        }
    except Exception as e:
        frappe.log_error(f"Erro ao consultar cadastro SEFAZ: {str(e)}")
        return {
            "success": False,
            "cStat": "Erro",
            "xMotivo": str(e)
        }


@frappe.whitelist()
def consultar_documento_sefaz(documento_fiscal):
    """Consulta o status oficial de uma NF-e por chave na SEFAZ"""
    if not documento_fiscal:
        frappe.throw(_("Documento Fiscal não informado."))

    dfe = frappe.get_doc("Documento Fiscal Eletronico", documento_fiscal)
    if not dfe.chave_acesso:
        frappe.throw(_("Este documento não possui chave de acesso para consulta."))

    try:
        nfe, amb_label, _ = get_sefaz_client(dfe.empresa)
        ret = nfe.consulta_documento(dfe.chave_acesso)
        resp = getattr(ret, "resposta", None)

        cstat = getattr(resp, "cStat", None) if resp else "Erro"
        xmotivo = getattr(resp, "xMotivo", None) if resp else "Sem resposta da SEFAZ"
        prot = getattr(resp, "protNFe", None) if resp else None
        infProt = getattr(prot, "infProt", None) if prot else None

        nProt = getattr(infProt, "nProt", None) if infProt else None
        dhRecbto = getattr(infProt, "dhRecbto", None) if infProt else None

        if cstat == "100":
            dfe.status = "Autorizado"
            dfe.codigo_status_sefaz = "100"
            dfe.mensagem_sefaz = xmotivo
            if nProt:
                dfe.protocolo = str(nProt)
            if dhRecbto:
                dfe.data_autorizacao = str(dhRecbto)
            dfe.save(ignore_permissions=True)
            frappe.db.commit()
        elif cstat == "101":
            dfe.status = "Cancelado"
            dfe.codigo_status_sefaz = "101"
            dfe.mensagem_sefaz = xmotivo
            dfe.save(ignore_permissions=True)
            frappe.db.commit()

        return {
            "success": True,
            "cStat": cstat,
            "xMotivo": xmotivo,
            "protocolo": nProt or dfe.protocolo,
            "chave_acesso": dfe.chave_acesso,
            "ambiente": amb_label
        }
    except Exception as e:
        frappe.log_error(f"Erro ao consultar documento SEFAZ: {str(e)}")
        return {
            "success": False,
            "cStat": "Erro",
            "xMotivo": str(e),
            "chave_acesso": dfe.chave_acesso
        }
