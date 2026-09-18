import frappe
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
import base64
from lxml import etree
import signxml

class SignerA1:
    """Assinador Digital XMLDSig ICP-Brasil para NF-e/NFC-e/CT-e"""
    def __init__(self, pfx_data, password):
        self.pfx_data = pfx_data
        self.password = password.encode('utf-8') if isinstance(password, str) else password
        self.private_key, self.certificate, self.additional_certificates = pkcs12.load_key_and_certificates(
            self.pfx_data, self.password
        )

    def sign_xml(self, xml_string, reference_uri=None):
        """Assina uma string XML no padrão da SEFAZ"""
        root = etree.fromstring(xml_string.encode('utf-8'))
        signer = signxml.XMLSigner(
            method=signxml.methods.enveloped,
            signature_algorithm='rsa-sha1',
            digest_algorithm='sha1',
            c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
        )
        signed_root = signer.sign(
            root,
            key=self.private_key,
            cert=self.certificate,
            reference_uri=reference_uri
        )
        return etree.tostring(signed_root, encoding='utf-8').decode('utf-8')
