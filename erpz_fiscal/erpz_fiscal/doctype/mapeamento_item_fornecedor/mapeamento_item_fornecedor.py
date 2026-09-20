import frappe
from frappe.model.document import Document

class MapeamentoItemFornecedor(Document):
    def validate(self):
        if not self.fator_conversao or self.fator_conversao <= 0:
            self.fator_conversao = 1.0
