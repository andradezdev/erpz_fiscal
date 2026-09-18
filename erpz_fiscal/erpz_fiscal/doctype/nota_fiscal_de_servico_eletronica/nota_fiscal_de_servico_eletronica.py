import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, get_datetime
import random

class NotaFiscaldeServicoEletronica(Document):
    def validate(self):
        self.calcular_totais()
        if not self.get("data_emissao"):
            self.data_emissao = now_datetime()

    def calcular_totais(self):
        vl_serv = flt(self.get("valor_servicos"))
        vl_ded = flt(self.get("valor_deducoes"))
        vl_desc = flt(self.get("valor_desconto"))
        
        base_iss = max(0, vl_serv - vl_ded - vl_desc)
        aliq_iss = flt(self.get("aliquota_iss", 2.90))
        vl_iss = base_iss * (aliq_iss / 100)
        
        v_pis = flt(self.get("valor_pis"))
        v_cofins = flt(self.get("valor_cofins"))
        v_inss = flt(self.get("valor_inss"))
        v_irrf = flt(self.get("valor_irrf"))
        v_csll = flt(self.get("valor_csll"))
        
        tot_ret = v_pis + v_cofins + v_inss + v_irrf + v_csll
        if self.get("iss_retido"):
            tot_ret += vl_iss

        self.base_calculo_iss = base_iss
        self.valor_iss = vl_iss
        self.total_retencoes = tot_ret
        self.valor_liquido = max(0, vl_serv - tot_ret - vl_desc)

        # Reforma Tributária (IBS e CBS sobre Serviços)
        aliq_ibs = flt(self.get("aliquota_ibs", 17.70))
        aliq_cbs = flt(self.get("aliquota_cbs", 8.80))
        self.valor_ibs = vl_serv * (aliq_ibs / 100)
        self.valor_cbs = vl_serv * (aliq_cbs / 100)

    @frappe.whitelist()
    def transmitir_prefeitura(self):
        """
        Roteador de Emissão da NFS-e:
        - Cenário 1: Gateway API Unificado (Focus NFe / PlugNotas / Nuvem Fiscal)
        - Cenário 2: Conexão Direta com Web Services Municipais / Padrão Nacional (A1 ICP-Brasil)
        - Cenário 3: Modo Demonstração / Sandbox
        """
        cfg_name = frappe.db.get_value("Configuracao Fiscal Empresa", {"empresa": self.get("empresa")}, "name")
        cfg = frappe.get_doc("Configuracao Fiscal Empresa", cfg_name) if cfg_name else None
        
        provedor_modo = (cfg.get("provedor_nfse") if cfg else "") or "1 - Gateway API Unificado"
        
        if "1 - Gateway" in provedor_modo:
            from erpz_fiscal.services.nfse_gateway import NFSeGateway
            gateway = NFSeGateway(cfg)
            res = gateway.enviar_nfse(self)
        elif "2 - Conexão Direta" in provedor_modo:
            from erpz_fiscal.services.nfse_direct import NFSeDirect
            direct = NFSeDirect(cfg)
            res = direct.enviar_nfse(self)
        else:
            numero = self.numero_nfse or random.randint(2026001, 2026999)
            chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            cod_verif = f"{''.join(random.choice(chars) for _ in range(4))}-{''.join(random.choice(chars) for _ in range(4))}"
            res = {
                "success": True,
                "status": "Autorizada",
                "numero_nfse": numero,
                "codigo_verificacao": cod_verif,
                "link": f"https://nfe.prefeitura.sp.gov.br/visualizacao?num={numero}&cod={cod_verif}",
                "mensagem": "NFS-e autorizada com sucesso em Modo Demonstração."
            }

        if res.get("success"):
            self.status = res.get("status", "Autorizada")
            self.numero_nfse = res.get("numero_nfse")
            self.codigo_verificacao = res.get("codigo_verificacao")
            self.link_visualizacao_prefeitura = res.get("link")
            self.mensagem_retorno = res.get("mensagem")
            self.data_emissao = now_datetime()
            self.save(ignore_permissions=True)
            frappe.db.commit()

        return res

    @frappe.whitelist()
    def cancelar_nfse(self, motivo="Cancelamento de serviço"):
        self.status = "Cancelada"
        self.mensagem_retorno = f"NFS-e cancelada. Motivo: {motivo}"
        self.save(ignore_permissions=True)
        frappe.db.commit()
        return {"success": True, "message": self.mensagem_retorno}
