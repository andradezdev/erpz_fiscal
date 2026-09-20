import re
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime, get_datetime
import random

class DocumentoFiscalEletronico(Document):
    def validate(self):
        self.aplicar_regras_tributarias()
        self.calcular_totais()
        if not self.get("data_emissao"):
            self.data_emissao = now_datetime()

    def aplicar_regras_tributarias(self):
        """
        Motor Fiscal: busca Regra de Tributacao para cada item e calcula
        ICMS, ICMS-ST, IPI, PIS, COFINS e os impostos da Reforma Tributária (IBS e CBS)
        """
        for item in (self.get("itens") or []):
            vl_prod = flt(item.get("quantidade", 1)) * flt(item.get("valor_unitario", 0))
            item.valor_total = vl_prod

            # Localiza Regra de Tributação mais adequada
            cfop_item = item.get("cfop") or "5102"
            regra_name = frappe.db.get_value("Regra de Tributacao", {"cfop": cfop_item}, "name")
            if not regra_name:
                regra_name = frappe.db.get_value("Regra de Tributacao", {}, "name")

            if regra_name:
                regra = frappe.get_doc("Regra de Tributacao", regra_name)
                
                # 1. ICMS Tradicional
                item.cst_icms = regra.cst_icms or "102"
                item.aliquota_icms = flt(regra.aliquota_icms)
                item.base_icms = vl_prod * (1 - flt(regra.reducao_base_icms) / 100)
                item.valor_icms = item.base_icms * (item.aliquota_icms / 100)

                # 2. ICMS-ST
                item.mva_st = flt(regra.mva_st)
                if item.mva_st > 0:
                    item.base_st = vl_prod * (1 + item.mva_st / 100)
                    item.aliquota_st = flt(regra.aliquota_icms_st or 18)
                    v_icms_proprio = item.valor_icms
                    item.valor_icms_st = max(0, (item.base_st * (item.aliquota_st / 100)) - v_icms_proprio)
                else:
                    item.base_st = 0
                    item.valor_icms_st = 0

                # 3. PIS e COFINS
                item.cst_pis = regra.cst_pis or "01"
                item.aliquota_pis = flt(regra.aliquota_pis)
                item.base_pis = vl_prod
                item.valor_pis = item.base_pis * (item.aliquota_pis / 100)

                item.cst_cofins = regra.cst_cofins or "01"
                item.aliquota_cofins = flt(regra.aliquota_cofins)
                item.base_cofins = vl_prod
                item.valor_cofins = item.base_cofins * (item.aliquota_cofins / 100)

                # 4. IPI
                item.cst_ipi = regra.cst_ipi or "53"
                item.aliquota_ipi = flt(regra.aliquota_ipi)
                item.base_ipi = vl_prod if item.aliquota_ipi > 0 else 0
                item.valor_ipi = item.base_ipi * (item.aliquota_ipi / 100)

                # 5. REFORMA TRIBUTÁRIA: IBS (Estadual/Municipal) e CBS (Federal)
                item.cst_ibs = regra.cst_ibs or "01"
                item.aliquota_ibs = flt(regra.aliquota_ibs if regra.aliquota_ibs is not None else 17.70)
                item.base_ibs = vl_prod
                item.valor_ibs = item.base_ibs * (item.aliquota_ibs / 100)

                item.cst_cbs = regra.cst_cbs or "01"
                item.aliquota_cbs = flt(regra.aliquota_cbs if regra.aliquota_cbs is not None else 8.80)
                item.base_cbs = vl_prod
                item.valor_cbs = item.base_cbs * (item.aliquota_cbs / 100)

                # 6. DIFAL / Partilha Interestadual (EC 87/2015)
                uf_dest = self.destinatario_uf or "SP"
                if uf_dest != "SP" and cint(self.destinatario_consumidor_final) == 1 and str(self.destinatario_indicador_ie or "").startswith("9"):
                    origem_item = str(frappe.db.get_value("Item", item.item_code, "origem_fiscal") or "0")
                    if origem_item[:1] in ("1", "2", "3", "8"):
                        aliq_inter = 4.0
                    elif uf_dest in ("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "PA", "PB", "PE", "PI", "RN", "RO", "RR", "SE", "TO"):
                        aliq_inter = 7.0
                    else:
                        aliq_inter = 12.0

                    aliq_dest = flt(item.aliquota_icms_uf_dest or 18.0)
                    aliq_fcp = flt(item.aliquota_fcp_uf_dest or 0.0)
                    difal_pct = max(0.0, aliq_dest - aliq_inter)

                    item.valor_bc_difal = vl_prod
                    item.aliquota_icms_inter = aliq_inter
                    item.aliquota_icms_uf_dest = aliq_dest
                    item.valor_difal_dest = round(vl_prod * (difal_pct / 100.0), 2)
                    item.valor_fcp_dest = round(vl_prod * (aliq_fcp / 100.0), 2)
                else:
                    item.valor_bc_difal = 0
                    item.valor_difal_dest = 0
                    item.valor_fcp_dest = 0
            else:
                item.valor_icms = 0
                item.valor_icms_st = 0
                item.valor_ipi = 0
                item.valor_pis = 0
                item.valor_cofins = 0
                item.base_ibs = vl_prod
                item.aliquota_ibs = 17.70
                item.valor_ibs = vl_prod * 0.177
                item.base_cbs = vl_prod
                item.aliquota_cbs = 8.80
                item.valor_cbs = vl_prod * 0.088

    def calcular_totais(self):
        itens = self.get("itens") or []
        tot_prod = sum(flt(i.get("valor_total")) for i in itens)
        tot_icms = sum(flt(i.get("valor_icms")) for i in itens)
        tot_st = sum(flt(i.get("valor_icms_st")) for i in itens)
        tot_ipi = sum(flt(i.get("valor_ipi")) for i in itens)
        tot_pis = sum(flt(i.get("valor_pis")) for i in itens)
        tot_cofins = sum(flt(i.get("valor_cofins")) for i in itens)
        tot_ibs = sum(flt(i.get("valor_ibs")) for i in itens)
        tot_cbs = sum(flt(i.get("valor_cbs")) for i in itens)
        tot_difal = sum(flt(i.get("valor_difal_dest")) for i in itens)
        tot_fcp = sum(flt(i.get("valor_fcp_dest")) for i in itens)
        tot_deson = sum(flt(i.get("valor_icms_desonerado")) for i in itens)
        
        self.valor_produtos = tot_prod
        self.valor_icms = tot_icms
        self.valor_icms_st = tot_st
        self.valor_ipi = tot_ipi
        self.valor_pis = tot_pis
        self.valor_cofins = tot_cofins
        self.valor_ibs = tot_ibs
        self.valor_cbs = tot_cbs
        self.total_difal_destino = tot_difal
        self.total_fcp_destino = tot_fcp
        self.total_icms_desonerado = tot_deson

        v_total_bruto = tot_prod + flt(self.get("valor_frete")) + tot_st + tot_ipi - flt(self.get("valor_desconto"))
        self.valor_total = v_total_bruto

        # Retenções Federais na Fonte (CSRF / IRRF / INSS)
        ret_pis = round(v_total_bruto * 0.0065, 2) if self.reter_csrf else 0.0
        ret_cofins = round(v_total_bruto * 0.03, 2) if self.reter_csrf else 0.0
        ret_csll = round(v_total_bruto * 0.01, 2) if self.reter_csrf else 0.0
        ret_irrf = round(v_total_bruto * 0.015, 2) if self.reter_irrf else 0.0
        ret_inss = round(v_total_bruto * 0.11, 2) if self.reter_inss else 0.0

        self.valor_retido_pis = ret_pis
        self.valor_retido_cofins = ret_cofins
        self.valor_retido_csll = ret_csll
        self.valor_retido_irrf = ret_irrf
        self.valor_retido_inss = ret_inss
        self.total_retencoes_federais = ret_pis + ret_cofins + ret_csll + ret_irrf + ret_inss
        self.valor_liquido_faturar = max(0.0, v_total_bruto - self.total_retencoes_federais)

    @frappe.whitelist()
    def gerar_chave_acesso(self):
        if not self.get("numero_nota"):
            self.atribuir_numero_nota()
        
        uf = "35"
        dt_emi = get_datetime(self.get("data_emissao") or now_datetime())
        ano_mes = dt_emi.strftime("%y%m")
        cnpj = "12345678000195"
        if frappe.db.exists("Configuracao Fiscal Empresa", self.get("empresa")):
            cfg = frappe.get_doc("Configuracao Fiscal Empresa", self.get("empresa"))
            cnpj = (cfg.cnpj or "12345678000195").replace(".", "").replace("-", "").replace("/", "")[:14]
        
        mod = "65" if "65" in (self.get("modelo_fiscal") or "") else "55"
        serie_str = str(self.get("serie") or 1).zfill(3)
        num_str = str(self.get("numero_nota") or 1).zfill(9)
        tp_emis = "1"
        codigo_num = str(random.randint(10000000, 99999999))
        
        chave_parcial = f"{uf}{ano_mes}{cnpj.zfill(14)}{mod}{serie_str}{num_str}{tp_emis}{codigo_num}"
        pesos = [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(chave_parcial[i]) * pesos[i] for i in range(43))
        resto = soma % 11
        dv = 0 if resto in [0, 1] else (11 - resto)
        
        self.chave_acesso = f"{chave_parcial}{dv}"
        return self.chave_acesso

    def atribuir_numero_nota(self):
        ultimo = frappe.db.sql("""
            SELECT MAX(numero_nota) FROM `tabDocumento Fiscal Eletronico`
            WHERE empresa = %s AND modelo_fiscal = %s AND serie = %s
        """, (self.get("empresa"), self.get("modelo_fiscal"), self.get("serie") or 1))[0][0] or 0
        self.numero_nota = ultimo + 1

    @frappe.whitelist()
    def transmitir_sefaz(self):
        # Validação do modo de operação da empresa
        modo_real = False
        if frappe.db.exists("Configuracao Fiscal Empresa", self.get("empresa")):
            cfg = frappe.get_doc("Configuracao Fiscal Empresa", self.get("empresa"))
            if "1 - Produção" in (cfg.get("modo_operacao") or "") or "Homologação Real" in (cfg.get("modo_operacao") or ""):
                modo_real = True

        if not self.get("chave_acesso"):
            self.gerar_chave_acesso()

        if modo_real:
            # 1. Validação de Certificado Digital A1 Ativo
            cert_valido = frappe.db.exists("Certificado Digital", {"empresa": self.get("empresa"), "status": "Ativo"})
            if not cert_valido:
                frappe.throw(_("Certificado Digital A1 não cadastrado ou inativo para a empresa {0}. Cadastre o arquivo .pfx e senha no menu Certificados Digitais para transmitir para a SEFAZ.").format(self.get("empresa")))

            # 2. Transmissão Real via WebService SEFAZ (mTLS)
            from erpz_fiscal.api.nfe import get_sefaz_client
            from erpz_fiscal.services.signer import SignerA1
            from erpbrasil.edoc.nfe import WS_NFE_AUTORIZACAO
            import datetime
            from lxml import etree

            nfe_client, amb_label, cert_doc = get_sefaz_client(self.get("empresa"))
            file_doc = frappe.get_doc("File", {"file_url": cert_doc.arquivo_pfx})
            pwd = cert_doc.get_password("senha_certificado") or cert_doc.senha_certificado

            # Assina o XML no padrão ICP-Brasil
            xml_nfe = self.montar_xml_nfe()
            signer = SignerA1(file_doc.get_content(), pwd)
            signed_nfe = signer.sign_xml(xml_nfe, reference_uri=f"NFe{self.chave_acesso}")
            self.xml_assinado = signed_nfe

            # Monta lote de envio síncrono
            lote_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            envi_nfe_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <idLote>{lote_id}</idLote>
  <indSinc>1</indSinc>
  {signed_nfe}
</enviNFe>"""

            endpoint = nfe_client._get_ws_endpoint(WS_NFE_AUTORIZACAO)
            trans = nfe_client._transmissao

            try:
                with trans.cliente(endpoint):
                    etree_doc = etree.fromstring(envi_nfe_str.encode("utf-8"))
                    res = trans.enviar("nfeAutorizacaoLote", etree_doc)
                    xml_text = res.text if hasattr(res, "text") else str(res)

                    ret_root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
                    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

                    infProt = ret_root.find(".//nfe:protNFe/nfe:infProt", ns) or ret_root.find(".//infProt")
                    retEnvi = ret_root.find(".//nfe:retEnviNFe", ns) or ret_root.find(".//retEnviNFe")

                    cstat = None
                    xmotivo = None
                    nprot = None
                    dhrecbto = None

                    if infProt is not None:
                        cstat = infProt.findtext("nfe:cStat", namespaces=ns) or infProt.findtext("cStat")
                        xmotivo = infProt.findtext("nfe:xMotivo", namespaces=ns) or infProt.findtext("xMotivo")
                        nprot = infProt.findtext("nfe:nProt", namespaces=ns) or infProt.findtext("nProt")
                        dhrecbto = infProt.findtext("nfe:dhRecbto", namespaces=ns) or infProt.findtext("dhRecbto")
                    elif retEnvi is not None:
                        cstat = retEnvi.findtext("nfe:cStat", namespaces=ns) or retEnvi.findtext("cStat")
                        xmotivo = retEnvi.findtext("nfe:xMotivo", namespaces=ns) or retEnvi.findtext("xMotivo")

                    self.codigo_status_sefaz = cstat or "999"
                    self.mensagem_sefaz = xmotivo or "Sem mensagem da SEFAZ"

                    if cstat == "100":
                        self.status = "Autorizado"
                        self.protocolo = str(nprot)
                        self.data_autorizacao = dhrecbto or now_datetime()
                        self.motivo_rejeicao = ""
                        self.xml_autorizado = xml_text
                        self.save(ignore_permissions=True)

                        vtype = self.get("voucher_type")
                        vno = self.get("voucher_no")
                        if vtype in ("Sales Invoice", "POS Invoice") and vno:
                            frappe.db.set_value(vtype, vno, {
                                "documento_fiscal": self.name,
                                "status_fiscal": "Autorizada",
                                "chave_nfe": self.chave_acesso,
                                "numero_nfe": self.numero_nota,
                                "serie_nfe": self.get("serie") or 1
                            })

                        frappe.db.commit()
                        return {
                            "success": True,
                            "status": "Autorizado",
                            "cStat": "100",
                            "numero_nota": self.numero_nota,
                            "protocolo": self.protocolo,
                            "chave_acesso": self.chave_acesso,
                            "mensagem": self.mensagem_sefaz
                        }
                    else:
                        self.status = "Rejeitado"
                        self.motivo_rejeicao = f"[{cstat}] {xmotivo}"
                        self.protocolo = ""
                        self.save(ignore_permissions=True)

                        vtype = self.get("voucher_type")
                        vno = self.get("voucher_no")
                        if vtype in ("Sales Invoice", "POS Invoice") and vno:
                            frappe.db.set_value(vtype, vno, {
                                "documento_fiscal": self.name,
                                "status_fiscal": "Rejeitada",
                                "chave_nfe": self.chave_acesso,
                                "numero_nfe": self.numero_nota,
                                "serie_nfe": self.get("serie") or 1
                            })

                        frappe.db.commit()
                        frappe.throw(_("Rejeição da SEFAZ ({0}): {1}").format(cstat, xmotivo))

            except Exception as e:
                self.status = "Rejeitado"
                self.mensagem_sefaz = str(e)
                self.motivo_rejeicao = str(e)
                self.save(ignore_permissions=True)
                frappe.db.commit()
                raise e

        # Modo de Simulação / Sandbox Interno
        self.status = "Autorizado"
        self.codigo_status_sefaz = "100"
        self.protocolo = f"13526{random.randint(100000000, 999999999)}"
        self.data_autorizacao = now_datetime()
        self.mensagem_sefaz = "Autorizado o uso da NF-e (100)" if "55" in (self.get("modelo_fiscal") or "") else "Autorizado o uso da NFC-e (100)"
        self.motivo_rejeicao = ""

        xml_proc = self.montar_proc_nfe()
        self.xml_assinado = xml_proc
        self.xml_autorizado = xml_proc
        self.save(ignore_permissions=True)

        vtype = self.get("voucher_type")
        vno = self.get("voucher_no")
        if vtype in ("Sales Invoice", "POS Invoice") and vno:
            frappe.db.set_value(vtype, vno, {
                "documento_fiscal": self.name,
                "status_fiscal": "Autorizada",
                "chave_nfe": self.chave_acesso,
                "numero_nfe": self.numero_nota,
                "serie_nfe": self.get("serie") or 1
            })

        frappe.db.commit()
        return {
            "success": True,
            "status": self.status,
            "cStat": self.codigo_status_sefaz,
            "numero_nota": self.numero_nota,
            "protocolo": self.protocolo,
            "chave_acesso": self.chave_acesso,
            "mensagem": self.mensagem_sefaz
        }
    @frappe.whitelist()
    def consultar_status_sefaz(self):
        if not self.get("chave_acesso"):
            frappe.throw(_("Documento fiscal não possui chave de acesso para consulta."))
            
        return {
            "status": self.status,
            "cStat": self.get("codigo_status_sefaz") or "100",
            "xMotivo": self.get("mensagem_sefaz") or "Autorizado o uso",
            "protocolo": self.get("protocolo"),
            "data_autorizacao": str(self.get("data_autorizacao") or now_datetime())
        }

    def montar_proc_nfe(self):
        xml_nfe = self.montar_xml_nfe()
        dt_aut = get_datetime(self.get("data_autorizacao") or now_datetime())
        dh_recbto = dt_aut.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        cstat = self.get("codigo_status_sefaz") or "100"
        motivo = self.get("mensagem_sefaz") or "Autorizado o uso da NF-e"
        
        is_nfce = "65" in (self.get("modelo_fiscal") or "")
        supl_tag = ""
        if is_nfce:
            supl_tag = f"""
<infNFeSupl>
  <qrCode>https://www.sefaz.sp.gov.br/nfce/qrcode?p={self.get('chave_acesso')}|2|2|000001|1234567890abcdef</qrCode>
  <urlChave>https://www.sefaz.sp.gov.br/nfce/consulta</urlChave>
</infNFeSupl>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
{xml_nfe}{supl_tag}
<protNFe versao="4.00">
  <infProt>
    <tpAmb>2</tpAmb>
    <verAplic>ERPZ-Fiscal-1.0</verAplic>
    <chNFe>{self.get("chave_acesso")}</chNFe>
    <dhRecbto>{dh_recbto}</dhRecbto>
    <nProt>{self.get("protocolo") or '135260000000001'}</nProt>
    <digVal>abcdef1234567890=</digVal>
    <cStat>{cstat}</cStat>
    <xMotivo>{motivo}</xMotivo>
  </infProt>
</protNFe>
</nfeProc>"""

    def montar_xml_nfe(self):
        tag_ref = ""
        fin_nfe = "1"
        if self.get("chave_nfe_referenciada"):
            clean_ref = re.sub(r'\D', '', self.get("chave_nfe_referenciada"))
            if len(clean_ref) == 44:
                tag_ref = f"""
      <NFref>
        <refNFe>{clean_ref}</refNFe>
      </NFref>"""
                fin_nfe = "4"

        dt_emi = get_datetime(self.get("data_emissao") or now_datetime())
        dh_emi = dt_emi.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        
        is_nfce = "65" in (self.get("modelo_fiscal") or "")
        mod_fiscal = "65" if is_nfce else "55"
        tp_imp = "4" if is_nfce else "1"
        
        cpf_cnpj = (self.get("destinatario_cpf_cnpj") or "").replace(".", "").replace("-", "").replace("/", "")
        tag_dest = ""
        if cpf_cnpj:
            if len(cpf_cnpj) > 11:
                tag_dest = f"""<dest>
      <CNPJ>{cpf_cnpj.zfill(14)}</CNPJ>
      <xNome>{self.get("destinatario_nome") or 'Cliente'}</xNome>
      <indIEDest>9</indIEDest>
    </dest>"""
            else:
                tag_dest = f"""<dest>
      <CPF>{cpf_cnpj.zfill(11)}</CPF>
      <xNome>{self.get("destinatario_nome") or 'Consumidor Final'}</xNome>
      <indIEDest>9</indIEDest>
    </dest>"""
        elif not is_nfce:
            tag_dest = """<dest>
      <CNPJ>47234356000153</CNPJ>
      <xNome>Cliente Consumidor</xNome>
      <indIEDest>9</indIEDest>
    </dest>"""
        
        itens_xml = ""
        v_bc_total = 0.0
        v_icms_total = 0.0
        v_pis_total = 0.0
        v_cofins_total = 0.0
        
        for idx, item in enumerate(self.get("itens") or [], 1):
            vl_item = flt(item.get("valor_total"))
            v_bc_total += vl_item
            v_icms_total += flt(item.get("valor_icms"))
            v_pis_total += flt(item.get("valor_pis"))
            v_cofins_total += flt(item.get("valor_cofins"))
            
            cbenef_tag = f"<cBenef>{item.get('codigo_beneficio_fiscal')}</cBenef>" if item.get("codigo_beneficio_fiscal") else ""
            
            tag_difal_item = ""
            if flt(item.get("valor_difal_dest")) > 0 or flt(item.get("valor_fcp_dest")) > 0:
                tag_difal_item = f"""
        <ICMSUFDest>
          <vBCUFDest>{flt(item.get("valor_bc_difal")):.2f}</vBCUFDest>
          <vBCFCPUFDest>{flt(item.get("valor_bc_difal")):.2f}</vBCFCPUFDest>
          <pFCPUFDest>{flt(item.get("aliquota_fcp_uf_dest")):.2f}</pFCPUFDest>
          <pICMSUFDest>{flt(item.get("aliquota_icms_uf_dest")):.2f}</pICMSUFDest>
          <pICMSInter>{flt(item.get("aliquota_icms_inter")):.2f}</pICMSInter>
          <pICMSInterPart>100.00</pICMSInterPart>
          <vFCPUFDest>{flt(item.get("valor_fcp_dest")):.2f}</vFCPUFDest>
          <vICMSUFDest>{flt(item.get("valor_difal_dest")):.2f}</vICMSUFDest>
          <vICMSUFRemet>0.00</vICMSUFRemet>
        </ICMSUFDest>"""

            itens_xml += f"""
    <det nItem="{idx}">
      <prod>
        <cProd>{item.get("item_code")}</cProd>
        <cEAN>SEM GTIN</cEAN>
        <xProd>{item.get("descricao")}</xProd>
        <NCM>{(item.get("ncm") or "00000000").replace(".", "")[:8].zfill(8)}</NCM>
        {cbenef_tag}
        <CFOP>{item.get("cfop") or ("5102" if is_nfce else "5102")}</CFOP>
        <uCom>{item.get("unidade") or "UN"}</uCom>
        <qCom>{flt(item.get("quantidade")):.4f}</qCom>
        <vUnCom>{flt(item.get("valor_unitario")):.4f}</vUnCom>
        <vProd>{vl_item:.2f}</vProd>
        <cEANTrib>SEM GTIN</cEANTrib>
        <uTrib>{item.get("unidade") or "UN"}</uTrib>
        <qTrib>{flt(item.get("quantidade")):.4f}</qTrib>
        <vUnTrib>{flt(item.get("valor_unitario")):.4f}</vUnTrib>
        <indTot>1</indTot>
      </prod>
      <imposto>
        <ICMS>
          <ICMS00>
            <orig>0</orig>
            <CST>{item.get("cst_icms") or ("102" if is_nfce else "00")}</CST>
            <modBC>3</modBC>
            <vBC>{vl_item:.2f}</vBC>
            <pICMS>{flt(item.get("aliquota_icms")):.2f}</pICMS>
            <vICMS>{flt(item.get("valor_icms")):.2f}</vICMS>
          </ICMS00>
        </ICMS>
        {tag_difal_item}
        <PIS>
          <PISAliq>
            <CST>{item.get("cst_pis") or "01"}</CST>
            <vBC>{vl_item:.2f}</vBC>
            <pPIS>{flt(item.get("aliquota_pis")):.2f}</pPIS>
            <vPIS>{flt(item.get("valor_pis")):.2f}</vPIS>
          </PISAliq>
        </PIS>
        <COFINS>
          <COFINSAliq>
            <CST>{item.get("cst_cofins") or "01"}</CST>
            <vBC>{vl_item:.2f}</vBC>
            <pCOFINS>{flt(item.get("aliquota_cofins")):.2f}</pCOFINS>
            <vCOFINS>{flt(item.get("valor_cofins")):.2f}</vCOFINS>
          </COFINSAliq>
        </COFINS>
      </imposto>
    </det>"""

        v_prod = flt(self.get("valor_produtos"))
        v_frete = flt(self.get("valor_frete"))
        v_desc = flt(self.get("valor_desconto"))
        v_total = v_prod + v_frete - v_desc
        v_trib = v_icms_total + v_pis_total + v_cofins_total

        obs_reforma = f"REFORMA TRIBUTARIA (EC 132/23): TOTAL IBS (17.7%): R$ {flt(self.get('valor_ibs')):.2f} | TOTAL CBS (8.8%): R$ {flt(self.get('valor_cbs')):.2f}."

        chave = self.get("chave_acesso") or ""
        c_nf = chave[35:43] if len(chave) >= 43 else "12345678"
        c_dv = chave[-1] if len(chave) == 44 else "1"

        
        ret_trib_tag = ""
        if flt(self.get("total_retencoes_federais")) > 0:
            ret_trib_tag = f"""
    <retTrib>
      <vRetPIS>{flt(self.get("valor_retido_pis")):.2f}</vRetPIS>
      <vRetCOFINS>{flt(self.get("valor_retido_cofins")):.2f}</vRetCOFINS>
      <vRetCSLL>{flt(self.get("valor_retido_csll")):.2f}</vRetCSLL>
      <vBCIRRF>{flt(self.get("valor_total")):.2f}</vBCIRRF>
      <vIRRF>{flt(self.get("valor_retido_irrf")):.2f}</vIRRF>
    </retTrib>"""

        transp_tag = """
    <transp>
      <modFrete>9</modFrete>
    </transp>"""
        if not is_nfce and (self.get("placa_veiculo") or flt(self.get("quantidade_volumes")) > 0):
            transp_tag = f"""
    <transp>
      <modFrete>0</modFrete>
      <transporta>
        <CNPJ>98765432000188</CNPJ>
        <xNome>{self.get("transportadora") or 'TRANSPORTADORA RAPIDO BRASIL LTDA'}</xNome>
        <IE>112233445566</IE>
        <xEnder>RUA DOS TRANSPORTES 500</xEnder>
        <xMun>SAO PAULO</xMun>
        <UF>SP</UF>
      </transporta>
      <veicTransp>
        <placa>{(self.get("placa_veiculo") or 'ABC1D23').replace('-', '').upper()}</placa>
        <UF>{self.get("uf_veiculo") or 'SP'}</UF>
        <RNTRC>12345678</RNTRC>
      </veicTransp>
      <vol>
        <qVol>{int(flt(self.get("quantidade_volumes") or 1))}</qVol>
        <esp>{self.get("especie_volumes") or 'VOLUMES'}</esp>
        <marca>DIVERSAS</marca>
        <pesoL>{flt(self.get("peso_liquido")):.3f}</pesoL>
        <pesoB>{flt(self.get("peso_bruto")):.3f}</pesoB>
      </vol>
    </transp>"""

        cobr_tag = """
    <pag>
      <detPag>
        <tPag>01</tPag>
        <vPag>{v_total:.2f}</vPag>
      </detPag>
    </pag>"""
        if not is_nfce:
            cobr_tag = f"""
    <cobr>
      <fat>
        <nFat>{str(self.get("numero_nota") or 1).zfill(6)}</nFat>
        <vOrig>{v_total:.2f}</vOrig>
        <vDesc>{v_desc:.2f}</vDesc>
        <vLiq>{v_total:.2f}</vLiq>
      </fat>
      <dup>
        <nDup>001</nDup>
        <dVenc>{dt_emi.strftime("%Y-%m-%d")}</dVenc>
        <vDup>{v_total:.2f}</vDup>
      </dup>
    </cobr>
    <pag>
      <detPag>
        <tPag>01</tPag>
        <vPag>{v_total:.2f}</vPag>
      </detPag>
    </pag>"""

        cnpj_emit = "18594769000140"
        ie_emit = "ISENTO"
        x_nome_emit = self.get("empresa") or "Empresa"
        x_fant_emit = "ERPZ"
        if frappe.db.exists("Configuracao Fiscal Empresa", self.get("empresa")):
            cfg = frappe.get_doc("Configuracao Fiscal Empresa", self.get("empresa"))
            cnpj_emit = (cfg.cnpj or cnpj_emit).replace(".", "").replace("-", "").replace("/", "")[:14]
            ie_emit = (cfg.inscricao_estadual or ie_emit).replace(".", "").replace("-", "").replace("/", "")

        return f"""<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe versao="4.00" Id="NFe{chave}">
    <ide>
      <cUF>35</cUF>
      <cNF>{c_nf}</cNF>
      <natOp>VENDA DE MERCADORIA</natOp>
      <mod>{mod_fiscal}</mod>
      <serie>{self.get("serie") or 1}</serie>
      <nNF>{self.get("numero_nota") or 1}</nNF>
      <dhEmi>{dh_emi}</dhEmi>
      <tpNF>1</tpNF>
      <idDest>1</idDest>
      <cMunFG>3550308</cMunFG>
      <tpImp>{tp_imp}</tpImp>
      <tpEmis>1</tpEmis>
      <cDV>{c_dv}</cDV>
      <tpAmb>2</tpAmb>
      <finNFe>{fin_nfe}</finNFe>{tag_ref}
      <indFinal>1</indFinal>
      <indPres>1</indPres>
      <procEmi>0</procEmi>
      <verProc>ERPZ Fiscal 1.0</verProc>
    </ide>
    <emit>
      <CNPJ>{cnpj_emit}</CNPJ>
      <xNome>{x_nome_emit}</xNome>
      <xFant>{x_fant_emit}</xFant>
      <enderEmit>
        <xLgr>AVENIDA PAULISTA</xLgr>
        <nro>1500</nro>
        <xBairro>BELA VISTA</xBairro>
        <cMun>3550308</cMun>
        <xMun>SAO PAULO</xMun>
        <UF>SP</UF>
        <CEP>01310100</CEP>
        <cPais>1058</cPais>
        <xPais>BRASIL</xPais>
        <fone>1130001234</fone>
      </enderEmit>
      <IE>{ie_emit}</IE>
      <CRT>3</CRT>
    </emit>
    {tag_dest}
    {itens_xml}
    <total>
      <ICMSTot>
        <vBC>{v_bc_total:.2f}</vBC>
        <vICMS>{v_icms_total:.2f}</vICMS>
        <vICMSDeson>{flt(self.get("total_icms_desonerado")):.2f}</vICMSDeson>
        <vFCP>0.00</vFCP>
        <vBCST>{flt(self.get("valor_icms_st")):.2f}</vBCST>
        <vST>{flt(self.get("valor_icms_st")):.2f}</vST>
        <vFCPST>0.00</vFCPST>
        <vFCPSTRet>0.00</vFCPSTRet>
        <vFCPUFDest>{flt(self.get("total_fcp_destino")):.2f}</vFCPUFDest>
        <vICMSUFDest>{flt(self.get("total_difal_destino")):.2f}</vICMSUFDest>
        <vICMSUFRemet>0.00</vICMSUFRemet>
        <vProd>{v_prod:.2f}</vProd>
        <vFrete>{v_frete:.2f}</vFrete>
        <vSeg>0.00</vSeg>
        <vDesc>{v_desc:.2f}</vDesc>
        <vII>0.00</vII>
        <vIPI>{flt(self.get("valor_ipi")):.2f}</vIPI>
        <vIPIDevol>0.00</vIPIDevol>
        <vPIS>{v_pis_total:.2f}</vPIS>
        <vCOFINS>{v_cofins_total:.2f}</vCOFINS>
        <vOutro>0.00</vOutro>
        <vNF>{v_total:.2f}</vNF>
        <vTotTrib>{v_trib:.2f}</vTotTrib>
      </ICMSTot>
    </total>
    {ret_trib_tag}
    {transp_tag}
    {cobr_tag}
    <infAdic>
      <infCpl>{obs_reforma}</infCpl>
    </infAdic>
  </infNFe>
</NFe>"""

    @frappe.whitelist()
    def cancelar_documento_sefaz(self, justificativa):
        """Cancela a NF-e/NFC-e na SEFAZ através do evento oficial 110111"""
        if self.status != "Autorizado":
            frappe.throw(_("Apenas documentos fiscais autorizados podem ser cancelados na SEFAZ."))

        if not justificativa or len(justificativa.strip()) < 15:
            frappe.throw(_("A justificativa de cancelamento deve conter no mínimo 15 caracteres conforme exigência legal da SEFAZ."))

        from erpz_fiscal.api.nfe import get_sefaz_client
        from erpz_fiscal.services.signer import SignerA1
        import datetime
        from lxml import etree

        nfe_client, amb_label, cert_doc = get_sefaz_client(self.empresa)
        file_doc = frappe.get_doc("File", {"file_url": cert_doc.arquivo_pfx})
        pwd = cert_doc.get_password("senha_certificado") or cert_doc.senha_certificado

        dh_evento = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        id_evento = f"ID110111{self.chave_acesso}01"
        cnpj_autor = cert_doc.cnpj_certificado or "18594769000140"
        tp_amb = "1" if "Produção" in amb_label else "2"

        evento_xml = f"""<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="{id_evento}">
    <cOrgao>35</cOrgao>
    <tpAmb>{tp_amb}</tpAmb>
    <CNPJ>{cnpj_autor}</CNPJ>
    <chNFe>{self.chave_acesso}</chNFe>
    <dhEvento>{dh_evento}</dhEvento>
    <tpEvento>110111</tpEvento>
    <nSeqEvento>1</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Cancelamento</descEvento>
      <nProt>{self.protocolo or '135260000000001'}</nProt>
      <xJust>{justificativa.strip()}</xJust>
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

        endpoint = "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl" if tp_amb == "2" else "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl"
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

                    if cstat in ("135", "136"):
                        self.status = "Cancelado"
                        self.codigo_status_sefaz = "101"
                        self.mensagem_sefaz = f"Cancelamento homologado ({cstat}): {xmotivo}"
                        self.save(ignore_permissions=True)

                        if self.voucher_type == "Sales Invoice" and self.voucher_no:
                            frappe.db.set_value("Sales Invoice", self.voucher_no, "status_fiscal", "Cancelada")
                        elif self.voucher_type == "POS Invoice" and self.voucher_no:
                            frappe.db.set_value("POS Invoice", self.voucher_no, "status_fiscal", "Cancelada")

                        frappe.db.commit()
                        return {"success": True, "cStat": cstat, "xMotivo": xmotivo, "protocolo": nprot}
                    else:
                        frappe.throw(_("SEFAZ Rejeitou o Cancelamento ({0}): {1}").format(cstat, xmotivo))
                else:
                    frappe.throw(_("Retorno inesperado da SEFAZ ao cancelar: {0}").format(xml_res[:300]))
        except Exception as e:
            frappe.log_error(f"Erro cancelamento SEFAZ: {str(e)}")
            raise e

    @frappe.whitelist()
    def emitir_cce_sefaz(self, texto_correcao):
        """Emite Carta de Correção Eletrônica (CC-e) na SEFAZ (Evento 110110)"""
        if self.status != "Autorizado":
            frappe.throw(_("Apenas documentos fiscais autorizados podem receber Carta de Correção."))

        if not texto_correcao or len(texto_correcao.strip()) < 15:
            frappe.throw(_("O texto da correção deve conter no mínimo 15 caracteres."))

        if len(texto_correcao.strip()) > 1000:
            frappe.throw(_("O texto da correção não pode exceder 1000 caracteres."))

        from erpz_fiscal.api.nfe import get_sefaz_client
        from erpz_fiscal.services.signer import SignerA1
        import datetime
        from lxml import etree

        nfe_client, amb_label, cert_doc = get_sefaz_client(self.empresa)
        file_doc = frappe.get_doc("File", {"file_url": cert_doc.arquivo_pfx})
        pwd = cert_doc.get_password("senha_certificado") or cert_doc.senha_certificado

        dh_evento = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        seq_evento = 1
        id_evento = f"ID110110{self.chave_acesso}{str(seq_evento).zfill(2)}"
        cnpj_autor = cert_doc.cnpj_certificado or "18594769000140"
        tp_amb = "1" if "Produção" in amb_label else "2"

        x_cond_uso = "A Carta de Correcao e disciplinada pelo paragrafo 1o-A do art. 7o do Convenio S/N, de 15 de dezembro de 1970 e pode ser utilizada para regularizacao de erro ocorrido na emissao de documento fiscal, desde que o erro nao esteja relacionado com: I - as variaveis que determinam o valor do imposto tais como: base de calculo, aliquota, diferenca de preco, quantidade, valor da operacao ou da prestacao; II - a correcao de dados cadastrais que implique mudanca do remetente ou do destinatario; III - a data de emissao ou de saida."

        evento_xml = f"""<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="{id_evento}">
    <cOrgao>35</cOrgao>
    <tpAmb>{tp_amb}</tpAmb>
    <CNPJ>{cnpj_autor}</CNPJ>
    <chNFe>{self.chave_acesso}</chNFe>
    <dhEvento>{dh_evento}</dhEvento>
    <tpEvento>110110</tpEvento>
    <nSeqEvento>{seq_evento}</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Carta de Correcao</descEvento>
      <xCorrecao>{texto_correcao.strip()}</xCorrecao>
      <xCondUso>{x_cond_uso}</xCondUso>
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

        endpoint = "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl" if tp_amb == "2" else "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx?wsdl"
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

                    if cstat in ("135", "136"):
                        return {"success": True, "cStat": cstat, "xMotivo": xmotivo, "protocolo": nprot, "sequencial": seq_evento}
                    else:
                        frappe.throw(_("SEFAZ Rejeitou a Carta de Correção ({0}): {1}").format(cstat, xmotivo))
                else:
                    frappe.throw(_("Retorno inesperado da SEFAZ na CC-e: {0}").format(xml_res[:300]))
        except Exception as e:
            frappe.log_error(f"Erro CC-e SEFAZ: {str(e)}")
            raise e
