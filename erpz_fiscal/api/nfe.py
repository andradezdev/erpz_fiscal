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

    # 3. Transmite para a SEFAZ
    try:
        res = dfe.transmitir_sefaz()
        so.db_set("documento_fiscal", dfe.name)
        so.db_set("numero_nfe", str(dfe.numero_nota))
        so.db_set("chave_nfe", dfe.chave_acesso)
        so.db_set("status_fiscal", "Autorizada" if dfe.status == "Autorizado" else "Rejeitada")
        frappe.db.commit()

        return {
            "success": dfe.status == "Autorizado",
            "sales_invoice": inv.name,
            "documento_fiscal": dfe.name,
            "numero_nfe": dfe.numero_nota,
            "chave_nfe": dfe.chave_acesso,
            "status": dfe.status,
            "mensagem": dfe.mensagem_sefaz or dfe.motivo_rejeicao
        }
    except Exception as e:
        so.db_set("documento_fiscal", dfe.name)
        so.db_set("numero_nfe", str(dfe.numero_nota))
        so.db_set("chave_nfe", dfe.chave_acesso)
        so.db_set("status_fiscal", "Rejeitada")
        frappe.db.commit()

        return {
            "success": False,
            "sales_invoice": inv.name,
            "documento_fiscal": dfe.name,
            "numero_nfe": dfe.numero_nota,
            "chave_nfe": dfe.chave_acesso,
            "status": "Rejeitado",
            "mensagem": str(e).replace("<", "&lt;").replace(">", "&gt;")
        }


@frappe.whitelist()
def imprimir_danfe(documento_fiscal=None, sales_invoice=None, sales_order=None, pos_invoice=None):
    """Gera e faz o download direto do DANFE ou Cupom NFC-e em PDF"""
    if not documento_fiscal:
        if pos_invoice:
            documento_fiscal = frappe.db.get_value("POS Invoice", pos_invoice, "documento_fiscal")
        elif sales_invoice:
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


def pos_invoice_on_submit(doc, method=None):
    """Hook de submissão do POS Invoice - a emissão de NFC-e é controlada pelo diálogo do caixa"""
    pass


@frappe.whitelist()
def emitir_nfce_pos_invoice(pos_invoice):
    """
    Emite a NFC-e (Modelo 65) a partir de uma POS Invoice (Venda no PDV)
    """
    if not pos_invoice:
        frappe.throw(_("Fatura do PDV não informada."))

    inv = frappe.get_doc("POS Invoice", pos_invoice)

    if inv.docstatus != 1:
        frappe.throw(_("A Fatura do PDV precisa estar submetida para emitir a NFC-e."))

    if inv.get("status_fiscal") == "Autorizada":
        frappe.throw(_("Esta venda no PDV já possui NFC-e autorizada: Nº {0}").format(inv.numero_nfe))

    # 1. Cria o Documento Fiscal Eletrônico Modelo 65 - NFC-e
    dfe = frappe.new_doc("Documento Fiscal Eletronico")
    dfe.modelo_fiscal = "65 - NFC-e"
    dfe.empresa = inv.company
    dfe.voucher_type = "POS Invoice"
    dfe.voucher_no = inv.name
    dfe.destinatario_tipo = "Customer"
    dfe.destinatario = inv.customer
    dfe.destinatario_nome = inv.customer_name or "Consumidor Final"
    dfe.destinatario_cpf_cnpj = inv.get("tax_id") or ""
    dfe.quantidade_volumes = 1
    dfe.especie_volumes = "VOLUMES"
    dfe.peso_liquido = 0.0
    dfe.peso_bruto = 0.0

    for item in inv.items:
        item_doc = frappe.get_doc("Item", item.item_code)
        dfe.append("itens", {
            "item_code": item.item_code,
            "descricao": item.item_name or item_doc.item_name,
            "ncm": item_doc.get("ncm") or "00000000",
            "cfop": "5102",
            "unidade": item.uom or "UN",
            "quantidade": item.qty,
            "valor_unitario": item.rate,
            "valor_total": item.amount,
            "cst_icms": "102"
        })

    dfe.calcular_totais()
    dfe.insert(ignore_permissions=True)

    # 2. Transmite para a SEFAZ
    try:
        res = dfe.transmitir_sefaz()
        inv.db_set("documento_fiscal", dfe.name)
        inv.db_set("numero_nfe", dfe.numero_nota)
        inv.db_set("serie_nfe", dfe.serie or 1)
        inv.db_set("chave_nfe", dfe.chave_acesso)
        inv.db_set("status_fiscal", "Autorizada" if dfe.status == "Autorizado" else "Rejeitada")
        frappe.db.commit()

        return {
            "success": dfe.status == "Autorizado",
            "pos_invoice": inv.name,
            "documento_fiscal": dfe.name,
            "numero_nfe": dfe.numero_nota,
            "chave_nfe": dfe.chave_acesso,
            "status": dfe.status,
            "mensagem": dfe.mensagem_sefaz or dfe.motivo_rejeicao
        }
    except Exception as e:
        inv.db_set("documento_fiscal", dfe.name)
        inv.db_set("numero_nfe", dfe.numero_nota)
        inv.db_set("serie_nfe", dfe.serie or 1)
        inv.db_set("chave_nfe", dfe.chave_acesso)
        inv.db_set("status_fiscal", "Rejeitada")
        frappe.db.commit()

        return {
            "success": False,
            "pos_invoice": inv.name,
            "documento_fiscal": dfe.name,
            "numero_nfe": dfe.numero_nota,
            "chave_nfe": dfe.chave_acesso,
            "status": "Rejeitado",
            "mensagem": str(e).replace("<", "&lt;").replace(">", "&gt;")
        }


@frappe.whitelist()
def sincronizar_mde_sefaz(empresa=None):
    """Consulta a SEFAZ Nacional via WebService NFeDistribuicaoDFe e sincroniza notas emitidas contra o CNPJ"""
    from erpz_fiscal.api.nfe import get_sefaz_client
    import base64, gzip
    from lxml import etree

    nfe_client, amb_label, cert_doc = get_sefaz_client(empresa)
    cnpj_autor = cert_doc.cnpj_certificado or "18594769000140"
    tp_amb = "1" if "Produção" in amb_label else "2"

    ultimo_nsu = frappe.db.sql("""
        SELECT MAX(CAST(nsu AS UNSIGNED)) FROM `tabManifestacao Destinatario NFe`
        WHERE empresa = %s AND nsu IS NOT NULL AND nsu != ''
    """, (cert_doc.empresa,))[0][0] or 0

    ult_nsu_str = str(ultimo_nsu).zfill(15)

    dist_xml = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>{tp_amb}</tpAmb>
  <cUFAutor>35</cUFAutor>
  <CNPJ>{cnpj_autor}</CNPJ>
  <distNSU>
    <ultNSU>{ult_nsu_str}</ultNSU>
  </distNSU>
</distDFeInt>"""

    endpoint = "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl" if tp_amb == "2" else "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl"
    trans = nfe_client._transmissao

    novas_notas = 0
    try:
        with trans.cliente(endpoint):
            etree_doc = etree.fromstring(dist_xml.encode("utf-8"))
            res = trans.enviar("nfeDistDFeInteresse", etree_doc)
            xml_res = res.text if hasattr(res, "text") else str(res)

            ret_root = etree.fromstring(xml_res.encode("utf-8") if isinstance(xml_res, str) else xml_res)
            ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

            cstat = ret_root.findtext(".//nfe:cStat", namespaces=ns) or ret_root.findtext(".//cStat")
            xmotivo = ret_root.findtext(".//nfe:xMotivo", namespaces=ns) or ret_root.findtext(".//xMotivo")

            docs_zip = ret_root.findall(".//nfe:docZip", ns) or ret_root.findall(".//docZip")
            for dz in docs_zip:
                schema = dz.get("schema", "")
                if dz.text:
                    gz_bytes = base64.b64decode(dz.text)
                    doc_unzipped = gzip.decompress(gz_bytes).decode("utf-8", errors="ignore")
                    doc_root = etree.fromstring(doc_unzipped.encode("utf-8"))
                    for elem in doc_root.getiterator():
                        if not hasattr(elem.tag, "find"):
                            continue
                        i = elem.tag.find("}")
                        if i >= 0:
                            elem.tag = elem.tag[i + 1:]

                    if "resNFe" in schema or doc_root.tag == "resNFe":
                        ch = doc_root.findtext("chNFe")
                        if ch and not frappe.db.exists("Manifestacao Destinatario NFe", {"chave_acesso": ch}):
                            mde = frappe.new_doc("Manifestacao Destinatario NFe")
                            mde.empresa = cert_doc.empresa
                            mde.chave_acesso = ch
                            mde.cnpj_emitente = doc_root.findtext("CNPJ") or doc_root.findtext("CPF") or ""
                            mde.nome_emitente = doc_root.findtext("xNome") or ""
                            mde.valor_total = flt(doc_root.findtext("vNF"))
                            dh_emi = doc_root.findtext("dhEmi")
                            if dh_emi:
                                mde.data_emissao = dh_emi[:19].replace("T", " ")
                            if len(ch) >= 34:
                                mde.serie = cint(ch[22:25])
                                mde.numero_nota = cint(ch[25:34])
                            mde.nsu = dz.get("NSU")
                            mde.situacao_manifestacao = "Sem Manifestação"
                            mde.insert(ignore_permissions=True)
                            novas_notas += 1

            frappe.db.commit()
            return {
                "success": True,
                "cStat": cstat,
                "xMotivo": xmotivo,
                "novas_notas": novas_notas,
                "ultimo_nsu": ult_nsu_str
            }
    except Exception as e:
        frappe.log_error(f"Erro sincronizacao MDe SEFAZ: {str(e)}")
        raise e


@frappe.whitelist()
def baixar_arquivo_sped_fiscal_txt(empresa=None, from_date=None, to_date=None, gerar_bloco_k=1):
    """Gera e retorna o conteúdo do arquivo TXT do SPED Fiscal EFD ICMS/IPI formatado para o PVA"""
    from erpz_fiscal.erpz_fiscal.report.sped_fiscal_efd_icms_ipi.sped_fiscal_efd_icms_ipi import execute
    cols, data = execute({
        "empresa": empresa,
        "from_date": from_date,
        "to_date": to_date,
        "gerar_bloco_k": gerar_bloco_k,
        "filtrar_bloco": "Todos os Blocos"
    })
    txt_content = "\r\n".join([d["linha"] for d in data]) + "\r\n"
    dt_ref = str(to_date or "20260930").replace("-", "")
    nome_arquivo = f"SPED_FISCAL_{empresa or 'EMPRESA'}_{dt_ref}.txt"
    return {
        "success": True,
        "conteudo_txt": txt_content,
        "nome_arquivo": nome_arquivo
    }


@frappe.whitelist()
def baixar_arquivo_efd_contribuicoes_txt(empresa=None, from_date=None, to_date=None):
    """Gera e retorna o arquivo TXT da EFD Contribuições (PIS/COFINS) para o PVA"""
    from erpz_fiscal.erpz_fiscal.report.efd_contribuicoes_pis_cofins.efd_contribuicoes_pis_cofins import execute
    cols, data = execute({
        "empresa": empresa,
        "from_date": from_date,
        "to_date": to_date
    })
    txt_content = "\r\n".join([d["linha"] for d in data]) + "\r\n"
    dt_ref = str(to_date or "20260930").replace("-", "")
    nome_arquivo = f"EFD_CONTRIBUICOES_{empresa or 'EMPRESA'}_{dt_ref}.txt"
    return {
        "success": True,
        "conteudo_txt": txt_content,
        "nome_arquivo": nome_arquivo
    }
