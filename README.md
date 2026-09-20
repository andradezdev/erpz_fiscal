# ERPZ Fiscal — Localização Fiscal Brasileira Oficial

Solução corporativa de **Localização Fiscal Brasileira** desenvolvida nativamente para o **Frappe Framework** e **ERPNext** (v16), inspirada nas melhores práticas da **OCA/l10n-brazil** e em conformidade estrita com o Manual de Orientação do Contribuinte (MOC 7.0 / SEFAZ 4.00), Reforma Tributária Nacional (EC 132/2023) e legislação do SPED.

Suporta emissão de **NF-e (Mod. 55)**, **NFC-e (Mod. 65)**, **NFS-e Dual-Mode**, **DIFAL e Partilha de ICMS (EC 87/2015)**, **Retenções Federais na Fonte (CSRF / IRRF / INSS)**, **Operações de Remessa e Retorno**, **Devoluções com Chave Referenciada (<NFref>)**, **Importação de XML de Compras (Inbound)** com De-Para automático, **Manifestação do Destinatário (MDe / Distribuição DF-e)**, **Eventos SEFAZ (Cancelamento e CC-e)**, motor de regras tributárias com cálculo automático de impostos (incluindo IBS/CBS), assinatura digital ICP-Brasil A1 via mTLS, geração de DANFE/Cupom térmico e **Monitor SEFAZ em tempo real**.

---

## Sumário Executivo

O **ERPZ Fiscal** moderniza a gestão fiscal no Frappe/ERPNext, substituindo módulos legados e monolíticos por uma arquitetura ágil, modular e auditável:
1. **Entrada Inteligente de Compras (Inbound)**: Importação de arquivos XML de fornecedores, cadastro automático de fornecedores, De-Para de códigos de produtos, conversão de unidades de medida (UOM), conversão de CFOP e geração automática em 1 clique de *Entrada no Estoque* (`Purchase Receipt`) e *Fatura de Compra* (`Purchase Invoice`).
2. **Manifestação do Destinatário (MDe / Distribuição DF-e)**: Consulta automática à SEFAZ Nacional via WebService por NSU, listando todas as notas emitidas contra o CNPJ da empresa, com registro de eventos (*Ciência da Emissão 210210*, *Confirmação 210200*, *Desconhecimento 210220*) e download do XML completo oficial.
3. **Eventos SEFAZ de Pós-Emissão**:
   - **Cancelamento Oficial na SEFAZ (`110111`)**: Transmissão via WebService com justificativa legal obrigatória e cancelamento automático de faturas e estoque.
   - **Carta de Correção Eletrônica - CC-e (`110110`)**: Transmissão oficial de correções permitidas pela legislação com controle sequencial.
   - **Notas Referenciadas (`<NFref>`)**: Suporte a notas de devolução referenciando a chave de acesso de 44 dígitos da nota de origem.
4. **Tributação Especial e Regras Avançadas**:
   - **DIFAL e Partilha de ICMS (EC 87/2015)**: Cálculo automático do diferencial de alíquotas e Fundo de Combate à Pobreza (FCP) para operações interestaduais com consumidor final não contribuinte, com geração das tags `<ICMSUFDest>` e totalizadores.
   - **Retenções Federais na Fonte (CSRF / IRRF / INSS)**: Apuração automática de retenções de PIS (0,65%), COFINS (3,00%), CSLL (1,00%), IRRF (1,50%) e INSS (11,00%), com geração da tag `<retTrib>` e dedução do valor líquido a faturar.
   - **Operações de Remessa e Retorno**: Matriz de CFOPs e regras tributárias automáticas para Remessa e Retorno de Conserto (5.915/5.916), Industrialização por Encomenda (5.901/5.902/5.124), Venda e Remessa para Entrega Futura (5.922/5.116) e Bonificação/Brinde (5.910).
   - **Desoneração de ICMS e Benefícios**: Tratamento de motivos de desoneração (`motDesICMS`), valor desonerado (`vICMSDeson`) e Código de Benefício Fiscal estadual (`cBenef`).
5. **Motor Tributário Automático**: Cálculo automático de ICMS, ICMS-ST (MVA), IPI, PIS, COFINS e os novos tributos da **Reforma Tributária (IBS 17,7% e CBS 8,8%)**.
6. **Emissão Oficial NF-e e NFC-e**: Geração do XML no leiaute SEFAZ 4.00, assinatura digital XMLDSig e transmissão direta aos WebServices estaduais.
7. **Impressão Oficial de DANFE**: Roteamento automático entre **DANFE A4 Retrato** (Mod. 55) e **Cupom Fiscal Térmico 80mm com QR Code v2.0** (Mod. 65) via `brazilfiscalreport`.
8. **NFS-e Municipal Dual-Mode**: Suporte a emissão de serviços via Gateway API REST (Focus NFe, PlugNotas, Nuvem Fiscal) ou Conexão Direta WebService Municipal / Padrão Nacional com certificado A1.
9. **Monitor SEFAZ & Consultas WebService**: Painel gerencial em formato de tabela com indicadores cStat, motivos de rejeição, totalizadores de IBS/CBS e botões de consulta em tempo real (Status do Serviço `107`, Consulta Situação de Nota `217` e Consulta Cadastro no CADESP `257`).

---

## 1. Arquitetura e Modelo de Dados

O aplicativo estrutura os dados em DocTypes nativos do Frappe, padronizados com identificadores ASCII no banco de dados e normalização de rótulos em português:

| DocType | Tipo | Finalidade |
| :--- | :--- | :--- |
| **`Documento Fiscal Eletronico`** | Principal | Registro do documento fiscal eletrônico (NF-e mod. 55 e NFC-e mod. 65). Armazena itens, totais, base de cálculo de impostos, DIFAL, FCP, retenções federais (`retTrib`), chave referenciada (`NFref`), XML assinado, XML autorizado, protocolo e status SEFAZ. |
| **`Importacao NFe Compra`** | Inbound | Importador inteligente de XML de compra. Faz a leitura do XML do fornecedor, vincula fornecedor, executa De-Para de itens e CFOPs e gera com 1 clique a Entrada de Estoque (`Purchase Receipt`) e a Fatura (`Purchase Invoice`). |
| **`Item Importacao NFe Compra`** | Tabela Filha | Linhas dos itens do XML importado com quantidades, unidades, impostos destacados e De-Para de produto interno. |
| **`Mapeamento Item Fornecedor`** | Cadastro | Tabela permanente de memória De-Para associando o código do produto no fornecedor (`cProd`) ao item interno do ERPNext com fator de conversão e CFOP padrão de entrada. |
| **`Manifestacao Destinatario NFe`** | MDe / DF-e | Gestão de notas emitidas contra o CNPJ da empresa localizadas na SEFAZ Nacional. Permite registrar Ciência da Emissão (`210210`), Confirmação (`210200`), Desconhecimento (`210220`), baixar o XML completo e disparar a importação de compras. |
| **`Configuracao Fiscal Empresa`** | Cadastro | Parametrização por empresa/filial: CNPJ, Inscrição Estadual, Regime Tributário (Simples Nacional / Regime Normal), Modo de Operação (Homologação / Produção), CSC e ID do CSC para NFC-e, e roteador de NFS-e. |
| **`Regra de Tributacao`** | Motor | Regras tributárias por CFOP, NCM e UF de destino. Define alíquotas, bases de cálculo, reduções, MVA para ICMS-ST, enquadramento de IPI, CSTs de PIS/COFINS e alíquotas de IBS/CBS. |
| **`Certificado Digital`** | Segurança | Armazenamento seguro de certificados digitais A1 (`.pfx` / `.p12`). Faz a extração automática do CNPJ do titular, validade de início/fim e status (*Ativo / Expirado*), com guarda de senha no cofre seguro. |
| **`Nota Fiscal de Servico Eletronica`** | Serviços | Emissão de NFS-e municipal com retenções federais (IRRF, PIS, COFINS, CSLL, INSS), ISSQN e IBS/CBS da Reforma Tributária. |

---

## 2. DIFAL e Partilha de ICMS (Emenda Constitucional 87/2015)

O ERPZ Fiscal automatiza a apuração do DIFAL para operações interestaduais destinadas a consumidor final não contribuinte:
* Identificação automática de operação interestadual (`destinatario_uf != emitente_uf`) com `destinatario_consumidor_final = 1` e `destinatario_indicador_ie = '9 - Não Contribuinte'`.
* Aplicação da alíquota interestadual (`pICMSInter`): 4% para produtos com conteúdo de importação (Origem 1, 2, 3, 8) e 7% ou 12% para produtos nacionais conforme a região de destino.
* Cálculo do DIFAL e FCP:
  $$	ext{DIFAL \%} = 	ext{Alíquota Interna UF Destino} - 	ext{Alíquota Interestadual}$$
  $$	ext{Valor DIFAL Destino} = 	ext{Base} 	imes \left(rac{	ext{DIFAL \%}}{100}ight)$$
  $$	ext{Valor FCP Destino} = 	ext{Base} 	imes \left(rac{	ext{Alíquota FCP \%}}{100}ight)$$
* Geração automática do grupo `<ICMSUFDest>` por item e totalizadores `<vICMSUFDest>` e `<vFCPUFDest>` no XML da NF-e.

---

## 3. Retenções Federais na Fonte (CSRF / IRRF / INSS)

Para fornecimento de mercadorias e serviços industriais sujeitos a retenção:
* **CSRF (PIS/COFINS/CSLL - 4,65%)**: PIS 0,65%, COFINS 3,00% e CSLL 1,00% (Lei 10.833/2003).
* **IRRF (1,50%)**: Imposto de Renda Retido na Fonte (Decreto 9.580/2018 - RIR).
* **INSS (11,00%)**: Retenção previdenciária sobre mão de obra.
* **Tag `<retTrib>`**: Montagem oficial no XML da NF-e com os valores retidos e dedução automática do valor líquido das duplicatas (`<dup>`) e do Contas a Receber.

---

## 4. Importador Inteligente de Compras (Inbound XML)

Automatiza 100% da escrituração de mercadorias no almoxarifado a partir do XML da NF-e emitida pelo fornecedor:
* **Identificação do Fornecedor**: Localiza ou cadastra o `Supplier` no ERPNext com base no CNPJ do XML.
* **Memória De-Para (`Mapeamento Item Fornecedor`)**: Associa o código do produto do fornecedor (`cProd`) ao item interno do catálogo.
* **Conversão de Unidades**: Converte embalagens (Caixa, Fardo) para a unidade de estoque interno.
* **De-Para de CFOP**: Converte CFOP de saída do fornecedor para entrada de industrialização (`1.101/2.101`) ou comercialização (`1.102/2.102`).
* **Geração em 1 Clique**: Cria a Entrada de Estoque (`Purchase Receipt`) e a Fatura de Compra (`Purchase Invoice`) com parcelas lidas das tags `<dup>`.

---

## 5. Manifestação do Destinatário (MDe / Distribuição DF-e)

* **Varredura por NSU**: Consulta automática ao WebService nacional `NFeDistribuicaoDFe` via Certificado Digital A1.
* **Eventos**: Ciência da Emissão (`210210`), Confirmação da Operação (`210200`) e Desconhecimento da Operação (`210220`).
* **Download do XML**: Baixa automática do pacote compactado (`gzip`) contendo o XML oficial da SEFAZ.

---

## 6. Eventos Oficiais SEFAZ (Cancelamento e CC-e)

* **Cancelamento de NF-e (`110111`)**: Transmissão oficial com justificativa legal mínima de 15 caracteres via `nfeRecepcaoEvento4`.
* **Carta de Correção Eletrônica - CC-e (`110110`)**: Transmissão oficial de correções com controle sequencial.
* **Devoluções com Chave Referenciada (`<NFref>`)**: Preenchimento automático da tag `<NFref><refNFe>...</refNFe></NFref>` e finalidade `4 - Devolução`.

---

## 7. Motor de Regras Tributárias e Reforma Tributária (IBS / CBS)

* **Tributos Tradicionais**: ICMS (Normal, Redução e FCP), ICMS-ST com MVA original e ajustada interestadual, IPI com Código de Enquadramento Legal, e PIS/COFINS (regimes cumulativo e não-cumulativo).
* **Reforma Tributária (EC 132/2023)**:
  * **IBS (Imposto sobre Bens e Serviços)**: Alíquota padrão calculada de **17,7%**.
  * **CBS (Contribuição sobre Bens e Serviços)**: Alíquota padrão calculada de **8,8%**.

---

## 8. Roteador de Impressão do DANFE (`brazilfiscalreport`)

* **NF-e (Modelo 55 - Mercadorias)**: DANFE oficial A4 Retrato com código de barras Code128C, canhoto de recebimento e quadro de tributos com IBS/CBS.
* **NFC-e (Modelo 65 - Consumidor / PDV)**: Cupom Fiscal em bobina térmica de 80mm com **QR Code oficial v2.0**.

---

## 9. Monitor SEFAZ & Consultas WebService

* **Monitor SEFAZ**: Painel gerencial em formato de tabela estruturada com linhas de grade nítidas, badges coloridos por status e filtros por Empresa, Período, Modelo e Status.
* **Consultas em Tempo Real**: Status do Serviço (`107`), Consulta de Nota (`217`) e Consulta de Cadastro no CADESP (`257`).

---

## 10. NFS-e Municipal Dual-Mode (Serviços)

* **Gateway API REST**: Integração com Focus NFe, PlugNotas (TecnoSpeed) e Nuvem Fiscal.
* **Conexão Direta Municipal**: Padrão ABRASF e prefeituras diretas assinando o RPS com o Certificado Digital A1.
* **Impressão do DANFSE**: Espelho oficial padrão nacional ABRASF em PDF.

---

## 11. Estrutura de Diretórios e Código-Fonte

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
│   │   ├── documento_fiscal_eletronico/ # NF-e, NFC-e, DIFAL, Retenções, Cancelamento, CC-e e NFref
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
