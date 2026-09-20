# ERPZ Fiscal — Localização Fiscal Brasileira Oficial

Solução corporativa de **Localização Fiscal Brasileira** desenvolvida nativamente para o **Frappe Framework** e **ERPNext** (v16), inspirada nas melhores práticas da **OCA/l10n-brazil** e em conformidade estrita com o Manual de Orientação do Contribuinte (MOC 7.0 / SEFAZ 4.00), Reforma Tributária Nacional (EC 132/2023) e legislação do SPED.

Suporta emissão de **NF-e (Mod. 55)**, **NFC-e (Mod. 65)**, **NFS-e Dual-Mode**, **Importação de XML de Compras (Inbound)** com De-Para automático, **Manifestação do Destinatário (MDe / Distribuição DF-e)**, **Eventos SEFAZ (Cancelamento e CC-e)**, motor de regras tributárias com cálculo automático de impostos (incluindo IBS/CBS), assinatura digital ICP-Brasil A1 via mTLS, geração de DANFE/Cupom térmico e **Monitor SEFAZ em tempo real**.

---

## Sumário Executivo

O **ERPZ Fiscal** moderniza a gestão fiscal no Frappe/ERPNext, substituindo módulos legados e monolíticos por uma arquitetura ágil, modular e auditável:
1. **Entrada Inteligente de Compras (Inbound)**: Importação de arquivos XML de fornecedores, cadastro automático de fornecedores, De-Para de códigos de produtos, conversão de unidades de medida (UOM), conversão de CFOP e geração automática em 1 clique de *Entrada no Estoque* (`Purchase Receipt`) e *Fatura de Compra* (`Purchase Invoice`).
2. **Manifestação do Destinatário (MDe / Distribuição DF-e)**: Consulta automática à SEFAZ Nacional via WebService por NSU, listando todas as notas emitidas contra o CNPJ da empresa, com registro de eventos (*Ciência da Emissão 210210*, *Confirmação 210200*, *Desconhecimento 210220*) e download do XML completo oficial.
3. **Eventos SEFAZ de Pós-Emissão**:
   - **Cancelamento Oficial na SEFAZ (`110111`)**: Transmissão via WebService com justificativa legal obrigatória e cancelamento automático de faturas e estoque.
   - **Carta de Correção Eletrônica - CC-e (`110110`)**: Transmissão oficial de correções permitidas pela legislação com controle sequencial.
   - **Notas Referenciadas (`<NFref>`)**: Suporte a notas de devolução referenciando a chave de acesso de 44 dígitos da nota de origem.
4. **Motor Tributário Automático**: Cálculo automático de ICMS, ICMS-ST (MVA), IPI, PIS, COFINS e os novos tributos da **Reforma Tributária (IBS 17,7% e CBS 8,8%)**.
5. **Emissão Oficial NF-e e NFC-e**: Geração do XML no leiaute SEFAZ 4.00, assinatura digital XMLDSig e transmissão direta aos WebServices estaduais.
6. **Impressão Oficial de DANFE**: Roteamento automático entre **DANFE A4 Retrato** (Mod. 55) e **Cupom Fiscal Térmico 80mm com QR Code v2.0** (Mod. 65) via `brazilfiscalreport`.
7. **NFS-e Municipal Dual-Mode**: Suporte a emissão de serviços via Gateway API REST (Focus NFe, PlugNotas, Nuvem Fiscal) ou Conexão Direta WebService Municipal / Padrão Nacional com certificado A1.
8. **Monitor SEFAZ & Consultas WebService**: Painel gerencial em formato de tabela com indicadores cStat, motivos de rejeição, totalizadores de IBS/CBS e botões de consulta em tempo real (Status do Serviço `107`, Consulta Situação de Nota `217` e Consulta Cadastro no CADESP `257`).

---

## 1. Arquitetura e Modelo de Dados

O aplicativo estrutura os dados em DocTypes nativos do Frappe, padronizados com identificadores ASCII no banco de dados e normalização de rótulos em português:

| DocType | Tipo | Finalidade |
| :--- | :--- | :--- |
| **`Documento Fiscal Eletronico`** | Principal | Registro do documento fiscal eletrônico (NF-e mod. 55 e NFC-e mod. 65). Armazena itens, totais, base de cálculo de impostos, XML assinado, XML autorizado, Chave de Acesso (44 dígitos), protocolo, chave referenciada e status SEFAZ. |
| **`Importacao NFe Compra`** | Inbound | Importador inteligente de XML de compra. Faz a leitura do XML do fornecedor, vincula fornecedor, executa De-Para de itens e CFOPs e gera com 1 clique a Entrada de Estoque (`Purchase Receipt`) e a Fatura (`Purchase Invoice`). |
| **`Item Importacao NFe Compra`** | Tabela Filha | Linhas dos itens do XML importado com quantidades, unidades, impostos destacados e De-Para de produto interno. |
| **`Mapeamento Item Fornecedor`** | Cadastro | Tabela permanente de memória De-Para associando o código do produto no fornecedor (`cProd`) ao item interno do ERPNext com fator de conversão e CFOP padrão de entrada. |
| **`Manifestacao Destinatario NFe`** | MDe / DF-e | Gestão de notas emitidas contra o CNPJ da empresa localizadas na SEFAZ Nacional. Permite registrar Ciência da Emissão (`210210`), Confirmação (`210200`), Desconhecimento (`210220`), baixar o XML completo e disparar a importação de compras. |
| **`Configuracao Fiscal Empresa`** | Cadastro | Parametrização por empresa/filial: CNPJ, Inscrição Estadual, Regime Tributário (Simples Nacional / Regime Normal), Modo de Operação (Homologação / Produção), CSC e ID do CSC para NFC-e, e roteador de NFS-e. |
| **`Regra de Tributacao`** | Motor | Regras tributárias por CFOP, NCM e UF de destino. Define alíquotas, bases de cálculo, reduções, MVA para ICMS-ST, enquadramento de IPI, CSTs de PIS/COFINS e alíquotas de IBS/CBS. |
| **`Certificado Digital`** | Segurança | Armazenamento seguro de certificados digitais A1 (`.pfx` / `.p12`). Faz a extração automática do CNPJ do titular, validade de início/fim e status (*Ativo / Expirado*), com guarda de senha no cofre seguro. |
| **`Nota Fiscal de Servico Eletronica`** | Serviços | Emissão de NFS-e municipal com retenções federais (IRRF, PIS, COFINS, CSLL, INSS), ISSQN e IBS/CBS da Reforma Tributária. |

---

## 2. Importador Inteligente de Compras (Inbound XML)

Automatiza 100% da escrituração de mercadorias no almoxarifado a partir do XML da NF-e emitida pelo fornecedor:

```
Arquivo XML da NF-e (Upload ou Baixado da SEFAZ)
   └── Identificação do Fornecedor (Localiza ou Cadastra Supplier no ERPNext)
         └── Leitura dos Itens e De-Para de Produtos (cProd Fornecedor ↔ Item Interno)
               └── Conversão de Unidades (UOM) e De-Para de CFOPs de Entrada
                     ├── [1 Clique] Entrada no Estoque (Purchase Receipt)
                     └── [1 Clique] Fatura de Compra & Contas a Pagar (Purchase Invoice)
```

* **Memória De-Para**: A associação realizada na primeira compra de um produto fica gravada permanentemente em `Mapeamento Item Fornecedor`. Nas compras seguintes do mesmo fornecedor, o reconhecimento é **100% automático**.
* **Duplicatas e Prazos**: O sistema lê as tags `<cobr><dup>` do XML e preenche a programação de pagamentos da fatura com as datas e valores reais negociados.

---

## 3. Manifestação do Destinatário (MDe / Distribuição DF-e)

Diretamente no ERPZ Fiscal, a empresa monitora e controla documentos fiscais emitidos contra o seu CNPJ no Brasil:
* **Varredura por NSU**: Consulta automática ao WebService nacional `NFeDistribuicaoDFe` via Certificado Digital A1.
* **Eventos de Manifestação**:
  * **`Ciência da Emissão` (210210)**: Toma conhecimento da nota fiscal e libera o download imediato do XML completo (`docZip` em gzip) pela SEFAZ.
  * **`Confirmação da Operação` (210200)**: Atesta formalmente o recebimento da mercadoria.
  * **`Desconhecimento da Operação` (210220)**: Protege a empresa contra notas "fantasmas" emitidas indevidamente por terceiros.
* **Botão `Importar para Estoque / Compras`**: Ao baixar o XML oficial da SEFAZ, um único clique cria a importação de compra e abre a tela de recebimento.

---

## 4. Eventos Oficiais SEFAZ (Cancelamento e CC-e)

* **Cancelamento de NF-e / NFC-e (`Evento 110111`)**:
  * Disparado pelo botão **`Cancelar NF-e na SEFAZ`** na tela do Documento Fiscal.
  * Exige justificativa com no mínimo 15 caracteres.
  * Transmite ao WebService `nfeRecepcaoEvento4`.
  * Ao homologar (`cStat 135`), atualiza a nota para **Cancelada**, grava o protocolo oficial e cancela a fatura correspondente no ERPNext.
* **Carta de Correção Eletrônica - CC-e (`Evento 110110`)**:
  * Disparada pelo botão **`Carta de Correção (CC-e)`**.
  * Controla o sequencial do evento (`nSeqEvento = 1, 2...`).
  * Ao homologar (`cStat 135`), registra o evento no histórico fiscal da nota.
* **Devoluções com Chave Referenciada (`<NFref>`)**:
  * Campo dedicado para informar a chave de 44 dígitos da nota de origem.
  * O sistema preenche a tag obrigatória `<ide><NFref><refNFe>...</refNFe></NFref></ide>` e define a finalidade da emissão como **4 - Devolução de Mercadoria**, prevenindo rejeições na SEFAZ.

---

## 5. Motor de Regras Tributárias e Reforma Tributária (IBS / CBS)

* **Tributos Tradicionais**: ICMS (Normal, Redução e FCP), ICMS-ST com MVA original e ajustada interestadual, IPI com Código de Enquadramento Legal, e PIS/COFINS (regimes cumulativo e não-cumulativo).
* **Reforma Tributária (EC 132/2023)**:
  * **IBS (Imposto sobre Bens e Serviços)**: Alíquota padrão calculada de **17,7%**.
  * **CBS (Contribuição sobre Bens e Serviços)**: Alíquota padrão calculada de **8,8%**.
  * Totalizadores segregados na NF-e, no XML e no Monitor SEFAZ.

---

## 6. Roteador de Impressão do DANFE (`brazilfiscalreport`)

* **NF-e (Modelo 55 - Mercadorias)**: DANFE oficial A4 Retrato com código de barras Code128C, canhoto de recebimento e quadro de tributos com IBS/CBS.
* **NFC-e (Modelo 65 - Consumidor / PDV)**: Cupom Fiscal em bobina térmica de 80mm com **QR Code oficial v2.0** para leitura por smartphone e validação na SEFAZ.

---

## 7. Consultas em Tempo Real ao WebService da SEFAZ

* **No Documento Fiscal**: Botão **`Consultar Situação na SEFAZ`** conecta com a chave de 44 dígitos (`cStat 100 - Autorizada`, `cStat 217 - Não consta na base`, `cStat 101 - Cancelada`).
* **No Certificado Digital A1**:
  * Botão **`Testar Conexão com SEFAZ`**: Executa ping no WebService estadual (`107 - Serviço em Operação`).
  * Botão **`Consultar Cadastro CADESP (SEFAZ)`**: Consulta a situação cadastral do CNPJ no CADESP estadual (`257 - Não habilitado`, `111 - Consulta cadastro com uma ocorrência`).

---

## 8. Painel Gerencial "Monitor SEFAZ"

Relatório analítico em formato de tabela estruturada com bordas e linhas nítidas, badges coloridos por status e filtros por Empresa, Período, Modelo e Status.

---

## 9. NFS-e Municipal Dual-Mode (Serviços)

* **Gateway API REST**: Integração com Focus NFe, PlugNotas (TecnoSpeed) e Nuvem Fiscal.
* **Conexão Direta Municipal**: Padrão ABRASF e prefeituras diretas assinando o RPS com o Certificado Digital A1.
* **Impressão do DANFSE**: Espelho oficial padrão nacional ABRASF em PDF.

---

## 10. Estrutura de Diretórios e Código-Fonte

```
erpz_fiscal/
├── api/
│   ├── __init__.py
│   └── nfe.py                     # APIs de faturamento, MDe, consultas SEFAZ e download DANFE
├── desktop_icon/
│   └── erpz_fiscal.json           # Ícone oficial no Desk
├── erpz_fiscal/
│   ├── doctype/
│   │   ├── certificado_digital/   # Cadastro e parsing de certificado A1 (.pfx)
│   │   ├── configuracao_fiscal_empresa/ # Parâmetros tributários por empresa
│   │   ├── documento_fiscal_eletronico/ # NF-e, NFC-e, Cancelamento, CC-e e NFref
│   │   ├── importacao_nfe_compra/ # Importador de XML de compra (Inbound)
│   │   ├── item_importacao_nfe_compra/ # Itens do XML e De-Para
│   │   ├── mapeamento_item_fornecedor/ # Memória permanente de De-Para de produtos
│   │   ├── manifestacao_destinatario_nfe/ # MDe e Distribuição DF-e por NSU
│   │   ├── nota_fiscal_de_servico_eletronica/ # NFS-e municipal Dual-Mode
│   │   └── regra_de_tributacao/   # Motor de regras de impostos e IBS/CBS
│   ├── report/
│   │   ├── monitor_sefaz/         # Monitor SEFAZ em tabela
│   │   └── sped_fiscal_efd_icms_ipi/ # Geração do SPED Fiscal ICMS/IPI
│   ├── workspace/
│   │   └── erpz_fiscal/           # Workspace com atalhos fiscais
│   └── workspace_sidebar/
│       └── erpz_fiscal.json       # Menu lateral oficial do ERPZ Fiscal
├── services/
│   ├── danfe.py                   # Roteador de impressão de DANFE A4 e Cupom 80mm
│   ├── nfse_direct.py             # Emissão direta NFS-e municipal via ABRASF
│   ├── nfse_gateway.py            # Emissão NFS-e via Gateway API REST
│   └── signer.py                  # Assinador XMLDSig ICP-Brasil A1 com XMLSignerWithSHA1
├── hooks.py
├── setup.py                       # Inicialização e vinculações de campos
└── pyproject.toml
```

---

## Licença

Distribuído sob licença MIT. Desenvolvido para o ecossistema ERPZ / Frappe Framework v16.
