# Estrutura dos Pareceres de Mérito — Debêntures incentivadas (SEI / MCID)

Este documento resume a **estrutura observada** em pareceres reais de enquadramento de projeto **prioritário** para **iluminação pública**, com captação por **debêntures incentivadas**, extraídos de processos SEI (amostra analisada em março/2026).

> **Âmbito:** o setor analisado nos exemplos é **iluminação pública** (subsetor prioritário), regulado pela **Portaria MCID nº 359, de 9 de abril de 2025**, em articulação com o **Decreto nº 11.964, de 26 de março de 2024**, a **Lei nº 12.431, de 24 de junho de 2011** e a **Lei nº 14.801, de 9 de janeiro de 2024**.  
> **Não confundir** com o Programa **Pró-Cidades** / **IN MCID nº 18/2025** (outro arcabouço).

---

## 1. Base normativa recorrente nos pareceres

| Instrumento | Papel no parecer |
|-------------|------------------|
| **Portaria MCID nº 359/2025** | Critérios complementares para enquadramento em **iluminação pública**; art. 1º remete à emissão sob **Lei 12.431/2011** e **Lei 14.801/2024** e ao **Decreto 11.964/2024**. |
| **Decreto nº 11.964/2024** | Projeto prioritário; setor **XV — iluminação pública**; titular do projeto (SPE, concessionária, etc.); dependência de **portaria ministerial prévia** quando exigida. |
| **Lei nº 12.431/2011** | Debêntures incentivadas (art. 2º, vinculação às despesas de capital). |
| **Lei nº 14.801/2024** | Citada no art. 1º da Portaria 359 junto à 12.431 (emissão / registro). |
| **Lei nº 14.600/2023** + **Decreto regimental** (12.553/2025 ou 11.468/2023, conforme época) | Competência do **DAC/SNDUM** e **CGMUR**. |
| **Decreto nº 12.002/2024** (art. 58) | Estrutura do **parecer de mérito** (itens I–VII); referência à **CONJUR** em pareceres recentes. |

---

## 2. Modelo de estrutura (município único ou SPE)

Ordem típica nos documentos analisados (ex.: pareceres sob Portaria 359 / debêntures):

| Seção | Título usual | Conteúdo |
|-------|----------------|----------|
| **1** | **SUMÁRIO EXECUTIVO** | Pedido à MCID; **enquadramento prioritário** (iluminação); **Portaria 359/2025**; valores totais e **parcela captada por debêntures incentivadas**; município(s) e população beneficiada. |
| **2** | **COMPETÊNCIA** | Art. 3º Portaria 359 (aprovação prévia MCID); art. 1º Portaria (Lei **12.431/2011** + Lei **14.801/2024** + § art. 4º Dec. 11.964); Lei 14.600 + Decreto regimental (DAC art. 18 ou 19). |
| **3** | **CRITÉRIOS E CONDIÇÕES** | **Decreto 11.964**: art. 2 (definições), art. 4 (setores — **XV iluminação**), art. 6 (aprovação ministerial). **Portaria 359**: arts. 5–10 (requisitos complementares, documentação, prazo 90 dias, conteúdo da futura portaria de aprovação). |
| **4** | **PROJETO** | Titular (SPE/concessionária); **carta-consulta** e documentos SEI anexos (CNPJ, QSA, quadros, contrato de concessão, etc.); síntese do objeto (modernização parque luminotécnico). |
| **5** | **O MUNICÍPIO** *(ou secção territorial antes do projeto, conforme documento)* | Dados IBGE, contexto urbano, população, IDH quando aplicável; em alguns casos esta parte aparece **após** critérios. |
| **6** | **REQUISITOS DO PARECER DE MÉRITO** | Transcrição / aderência ao **art. 58 do Decreto 12.002/2024** e, em exemplos recentes, menção a **Parecer CONJUR-MCID** (item 17). |
| **7** | **CONCLUSÃO / RECOMENDAÇÃO** | Síntese e encaminhamento. |

---

## 3. Variante: consórcio intermunicipal

Quando o titular atua sobre **vários municípios** via consórcio, surge frequentemente uma secção dedicada:

| Seção | Título | Conteúdo |
|-------|--------|----------|
| **3** *(alternativa)* | **O CONSÓRCIO** | Histórico, municípios, mapas, economia regional, PPP ou marcos (ex.: leilão B3), **antes** ou **em paralelo** com critérios jurídicos. |

O restante do documento mantém **Critérios e condições**, **Projeto** e **Requisitos do parecer de mérito**.

---

## 4. Alinhamento com o gerador do sistema (`motor.py`)

O gerador automático organiza o Markdown em **8 blocos** compatíveis com o fluxo de IA, **mapeados** para a lógica SEI:

| Gerador (app) | Correspondência SEI |
|----------------|---------------------|
| 1. Sumário Executivo | Igual. |
| 2. Competência | Texto fixo + base legal debêntures (ajustar à **Portaria 359** quando o objeto for IP). |
| 3. Identificação da proposta (Quadro 1) | Dados tabulares como nos SEI (valores, proponente, município). |
| 4. Dados do município / território | IBGE, CAPAG, IDH, contexto do objeto. |
| 5. Projeto e documentação | Descrição e valores da operação. |
| 6. Análise de enquadramento | Incorpora papel dos arts. **Dec. 11.964** e **Portaria 359** + **Lei 12.431** (conteúdo gerado por IA). |
| 7. Atendimento à documentação da operação | Texto sintético: critérios debêntures/CVM/Portaria 359; **sem** checklist Pró-Cidades (IN 18/2025) nem Quadro 3 nesse formato. Pendências formais derivam do crivo normativo + CAPAG. |
| 8. Conclusão | Viabilidade / pendências + CAPAG. |

Para **paridade total** com um parecer SEI (incluindo blocos longos de citação dos arts. 5º–10º da Portaria 359), seria necessário **template normativo** adicional ou **RAG** com PDF da Portaria — evolução futura.

---

## 5. Referências de data da Lei 12.431

Nos PDFs aparecem redações **“24 de junho de 2011”** e, noutros trechos, **“3 de junho de 2011”**. Ajustar sempre ao texto **consolidado** oficial (Planalto) na versão do parecer final.

---

## 6. Ficheiros de exemplo (origem)

Os PDFs foram analisados localmente a partir de cópias temporárias do WhatsApp; **não** são versionados no repositório. Para repetir a análise, use os números SEI nos nomes dos ficheiros indicados pelo utilizador.
