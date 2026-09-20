import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
import gzip, base64
from lxml import etree

class ManifestacaoDestinatarioNFe(Document):
    pass

    @frappe.whitelist()
    def dar_ciencia_emissao(self):
        return self.enviar_evento_manifestacao("210210", "Ciência da Emissão")

    @frappe.whitelist()
    def confirmar_operacao(self):
        return self.enviar_evento_manifestacao("210200", "Confirmação da Operação")

    @frappe.whitelist()
    def desconhecer_operacao(self):
        return self.enviar_evento_manifestacao("210220", "Desconhecimento da Operação")

    @frappe.whitelist()
    def operacao_nao_realizada(self, justificativa="Operação não realizada"):
        return self.enviar_evento_manifestacao("210240", "Operação não Realizada", justificativa=justificativa)

    def enviar_evento_manifestacao(self, codigo_evento, desc_evento, justificativa=None):
        from erpz_fiscal.api.nfe import get_sefaz_client
        from erpz_fiscal.services.signer import SignerA1
        from erpbrasil.edoc.nfe import WS_NFE_RECEPCAO_EVENTO
        import datetime

        nfe_client, amb_label, cert_doc = get_sefaz_client(self.empresa)
        file_doc = frappe.get_doc("File", {"file_url": cert_doc.arquivo_pfx})
        pwd = cert_doc.get_password("senha_certificado") or cert_doc.senha_certificado

        dh_evento = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        id_evento = f"ID{codigo_evento}{self.chave_acesso}01"
        cnpj_autor = cert_doc.cnpj_certificado or "18594769000140"
        tp_amb = "1" if "Produção" in amb_label else "2"

        just_tag = f"<xJust>{justificativa}</xJust>" if justificativa else ""

        evento_xml = f"""<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="{id_evento}">
    <cOrgao>91</cOrgao>
    <tpAmb>{tp_amb}</tpAmb>
    <CNPJ>{cnpj_autor}</CNPJ>
    <chNFe>{self.chave_acesso}</chNFe>
    <dhEvento>{dh_evento}</dhEvento>
    <tpEvento>{codigo_evento}</tpEvento>
    <nSeqEvento>1</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>{desc_evento}</descEvento>
      {just_tag}
    </detEvento>
  </infEvento>
</evento>"""

        signer = SignerA1(file_doc.get_content(), pwd)
        signed_evento = signer.sign_xml(evento_xml, reference_uri=id_evento)

        env_evento_lote = f"""<?xml version="1.0" encoding="UTF-8"?>
<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <idLote>1</idLote>
  {signed_evento}
</envEvento>"""

        # Transmite ao WebService de Eventos Nacional (cOrgao 91 - AN)
        endpoint = "https://hom.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl" if tp_amb == "2" else "https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl"
        trans = nfe_client._transmissao

        try:
            with trans.cliente(endpoint):
                etree_doc = etree.fromstring(env_evento_lote.encode("utf-8"))
                res = trans.enviar("nfeRecepcaoEvento", etree_doc)
                xml_res = res.text if hasattr(res, "text") else str(res)

                ret_root = etree.fromstring(xml_res.encode("utf-8") if isinstance(xml_res, str) else xml_res)
                ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

                infEvento = ret_root.find(".//nfe:retEvento/nfe:infEvento", ns) or ret_root.find(".//infEvento")
                if infEvento is not None:
                    cstat = infEvento.findtext("nfe:cStat", namespaces=ns) or infEvento.findtext("cStat")
                    xmotivo = infEvento.findtext("nfe:xMotivo", namespaces=ns) or infEvento.findtext("xMotivo")
                    nprot = infEvento.findtext("nfe:nProt", namespaces=ns) or infEvento.findtext("nProt")

                    self.mensagem_sefaz = f"[{cstat}] {xmotivo}"
                    if cstat in ("135", "136"): # Evento vinculado ou registrado
                        self.situacao_manifestacao = f"{desc_evento} ({codigo_evento})"
                        self.protocolo_manifestacao = nprot
                        self.data_manifestacao = now_datetime()
                        self.save(ignore_permissions=True)
                        frappe.db.commit()

                        # Se for Ciência ou Confirmação, tenta baixar o XML completo
                        if codigo_evento in ("210210", "210200"):
                            self.baixar_xml_completo()

                        return {"success": True, "cStat": cstat, "xMotivo": xmotivo, "protocolo": nprot}
                    else:
                        self.save(ignore_permissions=True)
                        frappe.db.commit()
                        frappe.throw(_("SEFAZ Rejeitou o Evento ({0}): {1}").format(cstat, xmotivo))
                else:
                    frappe.throw(_("Resposta inesperada da SEFAZ: {0}").format(xml_res[:300]))

        except Exception as e:
            frappe.log_error(f"Erro evento manifestacao MDe: {str(e)}")
            raise e

    @frappe.whitelist()
    def baixar_xml_completo(self):
        """Baixa o XML completo oficial da NF-e via WebService NFeDistribuicaoDFe"""
        from erpz_fiscal.api.nfe import get_sefaz_client
        from erpbrasil.edoc.nfe import WS_DFE_DISTRIBUICAO

        nfe_client, amb_label, cert_doc = get_sefaz_client(self.empresa)
        cnpj_autor = cert_doc.cnpj_certificado or "18594769000140"
        tp_amb = "1" if "Produção" in amb_label else "2"

        dist_xml = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>{tp_amb}</tpAmb>
  <cUFAutor>35</cUFAutor>
  <CNPJ>{cnpj_autor}</CNPJ>
  <consChave>
    <chNFe>{self.chave_acesso}</chNFe>
  </consChave>
</distDFeInt>"""

        endpoint = "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl" if tp_amb == "2" else "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl"
        trans = nfe_client._transmissao

        try:
            with trans.cliente(endpoint):
                etree_doc = etree.fromstring(dist_xml.encode("utf-8"))
                res = trans.enviar("nfeDistDFeInteresse", etree_doc)
                xml_res = res.text if hasattr(res, "text") else str(res)

                ret_root = etree.fromstring(xml_res.encode("utf-8") if isinstance(xml_res, str) else xml_res)
                ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

                docZip = ret_root.find(".//nfe:docZip", ns) or ret_root.find(".//docZip")
                if docZip is not None and docZip.text:
                    gz_bytes = base64.b64decode(docZip.text)
                    xml_unzipped = gzip.decompress(gz_bytes).decode("utf-8", errors="ignore")

                    self.xml_conteudo = xml_unzipped
                    self.tem_xml_completo = 1

                    # Salva arquivo anexo
                    file_name = f"NFe_{self.chave_acesso}.xml"
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "attached_to_doctype": self.doctype,
                        "attached_to_name": self.name,
                        "content": xml_unzipped,
                        "is_private": 1
                    })
                    _file.insert(ignore_permissions=True)
                    self.arquivo_xml = _file.file_url

                    self.save(ignore_permissions=True)
                    frappe.db.commit()
                    return {"success": True, "message": "XML completo baixado com sucesso!"}
                else:
                    cstat = ret_root.findtext(".//nfe:cStat", namespaces=ns) or ret_root.findtext(".//cStat")
                    xmotivo = ret_root.findtext(".//nfe:xMotivo", namespaces=ns) or ret_root.findtext(".//xMotivo")
                    return {"success": False, "cStat": cstat, "xMotivo": xmotivo}
        except Exception as e:
            frappe.log_error(f"Erro ao baixar XML DFe: {str(e)}")
            raise e

    @frappe.whitelist()
    def criar_importacao_compra(self):
        """Cria automaticamente uma Importação de Compra a partir do XML baixado"""
        if not self.arquivo_xml:
            frappe.throw(_("É necessário baixar o XML completo da SEFAZ antes de importar para o estoque."))

        if self.importacao_gerada:
            return {"importacao": self.importacao_gerada}

        imp = frappe.new_doc("Importacao NFe Compra")
        imp.empresa = self.empresa
        imp.arquivo_xml = self.arquivo_xml
        deposito = frappe.db.get_value("Warehouse", {"company": self.empresa, "is_group": 0}, "name")
        imp.deposito_padrao = deposito
        imp.insert(ignore_permissions=True)

        self.importacao_gerada = imp.name
        self.save(ignore_permissions=True)
        frappe.db.commit()

        return {"importacao": imp.name}
