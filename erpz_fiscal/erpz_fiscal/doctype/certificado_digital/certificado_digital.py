import frappe
from frappe import _
from frappe.model.document import Document
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime, timezone
import re

class CertificadoDigital(Document):
    def validate(self):
        self.verificar_validade()

    def verificar_validade(self):
        if not self.arquivo_pfx:
            return

        # Obter senha informada no form ou já gravada no cofre do Frappe
        password = self.senha_certificado
        if not password and not self.is_new():
            try:
                password = self.get_password("senha_certificado")
            except Exception:
                pass

        if not password:
            return

        try:
            file_doc = frappe.get_doc("File", {"file_url": self.arquivo_pfx})
            content = file_doc.get_content()
        except Exception as e:
            frappe.throw(_("Não foi possível carregar o arquivo do certificado: {0}").format(str(e)))

        try:
            pwd_bytes = password.encode("utf-8") if isinstance(password, str) else password
            _, cert, _ = pkcs12.load_key_and_certificates(content, pwd_bytes)
            if cert:
                dt_inicio = getattr(cert, "not_valid_before_utc", None) or getattr(cert, "not_valid_before", None)
                dt_fim = getattr(cert, "not_valid_after_utc", None) or getattr(cert, "not_valid_after", None)

                if dt_inicio:
                    if hasattr(dt_inicio, "tzinfo") and dt_inicio.tzinfo:
                        dt_inicio = dt_inicio.replace(tzinfo=None)
                    self.validade_inicio = dt_inicio.strftime("%Y-%m-%d %H:%M:%S")

                if dt_fim:
                    if hasattr(dt_fim, "tzinfo") and dt_fim.tzinfo:
                        dt_fim = dt_fim.replace(tzinfo=None)
                    self.validade_fim = dt_fim.strftime("%Y-%m-%d %H:%M:%S")

                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                if dt_fim:
                    self.status = "Ativo" if now_utc <= dt_fim else "Expirado"

                # Extrai CNPJ do sujeito do certificado A1 (ICP-Brasil)
                subj_str = ""
                for attr in cert.subject:
                    subj_str += f"{attr.oid._name}={attr.value}, "

                cnpj_match = re.search(r':(\d{14})', subj_str) or re.search(r'\b(\d{14})\b', subj_str)
                if cnpj_match:
                    self.cnpj_certificado = cnpj_match.group(1)

        except Exception as e:
            self.status = "Inválido"
            frappe.log_error(f"Erro ao ler certificado digital: {str(e)}")
            frappe.throw(_("Senha do certificado incorreta ou arquivo PFX corrompido: {0}").format(str(e)))
