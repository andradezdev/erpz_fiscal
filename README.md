# ERPZ Fiscal — Localização Fiscal Brasileira Oficial

Solução corporativa de **Localização Fiscal Brasileira** desenvolvida nativamente para o **Frappe Framework** e **ERPNext** (v16), inspirada nas melhores práticas da **OCA/l10n-brazil** e em conformidade estrita com o Manual de Orientação do Contribuinte (MOC 7.0 / SEFAZ 4.00), Reforma Tributária Nacional (EC 132/2023) e legislação do SPED.

Suporta emissão de **NF-e (Mod. 55)**, **NFC-e (Mod. 65)**, **NFS-e Dual-Mode**, motor de regras tributárias com cálculo automático de impostos, assinatura digital ICP-Brasil A1 via mTLS, geração de DANFE/Cupom térmico e **Monitor SEFAZ em tempo real**.

---

## Sumário Executivo

O **ERPZ Fiscal** moderniza a gestão fiscal no Frappe/ERPNext, substituindo módulos legados e monolíticos por uma arquitetura ágil, modular e auditável:
1. **Motor Tributário Automático**: Cálculo automático de ICMS, ICMS-ST (MVA), IPI, PIS, COFINS e os novos tributos da **Reforma Tributária (IBS 17,7% e CBS 8,8%)**.
2. **Emissão Oficial NF-e e NFC-e**: Geração do XML no leiaute SEFAZ 4.00, assinatura digital XMLDSig e transmissão direta aos WebServices estaduais.
3. **Impressão Oficial de DANFE**: Roteamento automático entre **DANFE A4 Retrato** (Mod. 55) e **Cupom Fiscal Térmico 80mm com QR Code v2.0** (Mod. 65) via `brazilfiscalreport`.
4. **NFS-e Municipal Dual-Mode**: Suporte a emissão de serviços via Gateway API REST (Focus NFe, PlugNotas, Nuvem Fiscal) ou Conexão Direta WebService Municipal / Padrão Nacional com certificado A1.
5. **Monitor SEFAZ & Consultas WebService**: Painel gerencial em formato de tabela com indicadores cStat, motivos de rejeição, totalizadores de IBS/CBS e botões de consulta em tempo real (Status do Serviço `107`, Consulta Situação de Nota `217` e Consulta Cadastro no CADESP `257`).

---

## 1. Arquitetura e Modelo de Dados

O aplicativo estrutura os dados em DocTypes nativos do Frappe, padronizados com identificadores ASCII no banco de dados e normalização de rótulos em português:

| DocType | Tipo | Finalidade |
| :--- | :--- | :--- |
| **`Documento Fiscal Eletronico`** | Principal | Registro do documento fiscal eletrônico (NF-e mod. 55 e NFC-e mod. 65). Armazena itens, totais, base de cálculo de impostos, XML assinado, XML autorizado, Chave de Acesso (44 dígitos), protocolo e status SEFAZ. |
| **`Configuracao Fiscal Empresa`** | Cadastro | Parametrização por empresa/filial: CNPJ, Inscrição Estadual, Regime Tributário (Simples Nacional / Regime Normal), Modo de Operação (Homologação / Produção), CSC e ID do CSC para NFC-e, e roteador de NFS-e. |
| **`Regra de Tributacao`** | Motor | Regras tributárias por CFOP, NCM e UF de destino. Define alíquotas, bases de cálculo, reduções, MVA para ICMS-ST, enquadramento de IPI, CSTs de PIS/COFINS e alíquotas de IBS/CBS. |
| **`Certificado Digital`** | Segurança | Armazenamento seguro de certificados digitais A1 (`.pfx` / `.p12`). Faz a extração automática do CNPJ do titular, validade de início/fim e status (*Ativo / Expirado*), com guarda de senha no cofre seguro. |
| **`Nota Fiscal de Servico Eletronica`** | Serviços | Emissão de NFS-e municipal com retenções federais (IRRF, PIS, COFINS, CSLL, INSS), ISSQN e IBS/CBS da Reforma Tributária. |

---

## 2. Motor de Regras Tributárias e Reforma Tributária (IBS / CBS)

O motor fiscal calcula os impostos linha a linha a partir dos dados do item (`ncm`, `cest`, `origem_fiscal`) e da operação (`cfop`, `uf_destino`):

### 2.1 Tributos Tradicionais
* **ICMS**: Base de cálculo normal, redução de base, alíquota interna e interestadual, Fundo de Combate à Pobreza (FCP).
* **ICMS-ST**: Cálculo de Margem de Valor Agregado (MVA original e MVA ajustada para operações interestaduais), apurando a retenção de ICMS-ST.
* **IPI**: Alíquota e Código de Enquadramento Legal (CEnq).
* **PIS e COFINS**: Regime cumulativo e não-cumulativo (CST 01, 02, 04, 06, 07, 08, 49, 99).

### 2.2 Reforma Tributária (Emenda Constitucional 132/2023)
O ERPZ Fiscal já incorpora os novos tributos sobre o consumo:
* **IBS (Imposto sobre Bens e Serviços)**: Alíquota padrão calculada de **17,7%**, com totalizador segregado.
* **CBS (Contribuição sobre Bens e Serviços)**: Alíquota padrão calculada de **8,8%**, com totalizador segregado.
* Os valores de IBS e CBS constam no Documento Fiscal, no XML SEFAZ e são consolidados no **Monitor SEFAZ**.

---

## 3. Assinatura Digital e Transmissão SEFAZ

O módulo integra criptografia e comunicação oficial sem depender de executáveis proprietários ou sistemas legados:

```
Documento Fiscal (ERPZ)
   └── Geração do XML 4.00 (NFe / NFCe)
         └── Canonicalização C14N e Assinatura Digital XMLDSig (SHA-1 / RSA)
               └── Transmissão mTLS via SOAP (nfeAutorizacaoLote)
                     └── Retorno Oficial SEFAZ (cStat 100 / Protocolo / Recibo)
                           └── Geração do DANFE Oficial em PDF
```

* **`SignerA1` (`erpz_fiscal.services.signer`)**: Executa a assinatura digital no padrão W3C XMLDSig ICP-Brasil sobre a tag `<infNFe Id="NFe...">`.
* **Transmissão mTLS**: Comunicação bidirecional direta contra os WebServices da SEFAZ utilizando o certificado A1 carregado na sessão HTTP/SOAP.

---

## 4. Roteador de Impressão do DANFE (`brazilfiscalreport`)

O sistema formata a impressão de acordo com o modelo fiscal emitido:

1. **NF-e (Modelo 55 - Mercadorias)**:
   * Gera o **DANFE oficial em folha A4 formato retrato**.
   * Contém código de barras Code128C para leitura óptica da chave de acesso.
   * Canhoto de recebimento destacado.
   * Detalhamento completo de bases de cálculo, ICMS, IPI, ST e quadro de IBS/CBS.
2. **NFC-e (Modelo 65 - Consumidor)**:
   * Gera o **Cupom Fiscal em bobina térmica de 80mm**.
   * Contém a montagem automática da tag `<infNFeSupl>` e o **QR Code oficial v2.0** para leitura por smartphone e validação na SEFAZ estadual.

---

## 5. Consultas em Tempo Real ao WebService da SEFAZ

Diretamente pela interface do usuário, é possível disparar comandos de auditoria fiscal:

* **No Documento Fiscal**: Botão **`Consultar Situação na SEFAZ`** conecta no WebService estadual com a chave de 44 dígitos e exibe em popup o status oficial (`cStat 100 - Autorizada`, `cStat 217 - Não consta na base`, `cStat 101 - Cancelada`).
* **No Certificado Digital A1**:
  * Botão **`Testar Conexão com SEFAZ`**: Executa ping contra o WebService `nfeStatusServico4` e confirma a disponibilidade da SEFAZ (`107 - Serviço em Operação`).
  * Botão **`Consultar Cadastro CADESP (SEFAZ)`**: Executa o serviço `nfeConsultaCadastro4` pelo CNPJ do certificado e valida se a empresa possui Inscrição Estadual e está habilitada para emitir NF-e.

---

## 6. Painel Gerencial "Monitor SEFAZ"

Relatório analítico disponível no menu lateral **ERPZ Fiscal &rarr; Monitor SEFAZ**:
* **Gráficos e KPIs**: Total de documentos, total de notas autorizadas (`100`), total de notas rejeitadas com erro e montante acumulado de tributos da Reforma (IBS e CBS).
* **Tabela Formatada com Linhas de Grade**:
  * Colunas: `Nº`, `Série`, `Modelo`, `Documento`, `Data Emissão`, `Destinatário`, `Status SEFAZ`, `Motivo SEFAZ (xMotivo)`, `Total (R$)`, `IBS`, `CBS`, `Protocolo` e `Chave de Acesso`.
  * Badges visuais com cores padronizadas: Verde para Autorizadas (`100`), Vermelho para Rejeições (`539`, etc.), Amarelo para Processando (`105`) e Cinza para Canceladas (`101`).
  * Filtros dinâmicos por Empresa, Período (*De / Até*), Modelo Fiscal e Status.

---

## 7. NFS-e Municipal Dual-Mode (Serviços)

O DocType **`Nota Fiscal de Servico Eletronica`** permite emissão de serviços municipais com flexibilidade de canal:
1. **Gateway API REST**: Integração com Focus NFe, PlugNotas (TecnoSpeed) e Nuvem Fiscal, cobrindo centenas de municípios simultaneamente via JSON REST.
2. **Conexão Direta WebService Municipal**: Conexão direta padrão ABRASF (ex: São Paulo - SP Nota Paulistana, Ginfes, ISSNet, etc.) assinando o RPS com o Certificado Digital A1.
3. **Impressão do DANFSE**: Visualização e impressão do espelho oficial do RPS / DANFSE padrão nacional.

---

## 8. Estrutura de Diretórios e Código-Fonte

```
erpz_fiscal/
├── api/
│   ├── __init__.py
│   └── nfe.py                     # APIs de faturamento SO, consultas SEFAZ e download DANFE
├── desktop_icon/
│   └── erpz_fiscal.json           # Ícone oficial persistente no Desk
├── erpz_fiscal/
│   ├── doctype/
│   │   ├── certificado_digital/   # Cadastro e parsing de certificado A1 (.pfx)
│   │   ├── configuracao_fiscal_empresa/ # Parâmetros por empresa e ambiente
│   │   ├── documento_fiscal_eletronico/ # NF-e, NFC-e, transmissão e XMLs
│   │   ├── nota_fiscal_de_servico_eletronica/ # NFS-e municipal
│   │   └── regra_de_tributacao/   # Motor de regras de impostos e IBS/CBS
│   ├── report/
│   │   ├── monitor_sefaz/         # Relatório em tabela do Monitor SEFAZ
│   │   └── sped_fiscal_efd_icms_ipi/ # Geração do SPED Fiscal ICMS/IPI
│   ├── workspace/
│   │   └── erpz_fiscal/           # Workspace com atalhos e cards
│   └── workspace_sidebar/
│       └── erpz_fiscal.json       # Menu lateral oficial do ERPZ Fiscal
├── services/
│   ├── danfe.py                   # Roteador de impressão de DANFE A4 e Cupom 80mm
│   ├── nfse_direct.py             # Emissão direta NFS-e municipal via ABRASF
│   ├── nfse_gateway.py            # Emissão NFS-e via Gateway API REST
│   └── signer.py                  # Assinador XMLDSig ICP-Brasil A1
├── hooks.py
├── setup.py                       # Criação de campos customizados e inicialização
└── pyproject.toml
```

---

## Licença

Distribuído sob licença MIT. Desenvolvido para o ecossistema ERPZ / Frappe Framework v16.
