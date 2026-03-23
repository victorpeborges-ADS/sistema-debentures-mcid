# Biblioteca — Debêntures incentivadas

## O que entra aqui

- Ficheiros **`.md`** em `pareceres_validados/`: pareceres **já validados pela equipa**, alinhados à **Lei nº 12.431/2011** e ao fluxo de **debêntures incentivadas** (não Pro-Cidades).

## Ruído que o sistema remove sozinho

Ficheiros cujo texto pareça **Parecer Pro-Cidades** (ex.: menção a “Pró-Cidades”, “programa pró-cidades”, ou padrão **8.6.6.3.4** da IN 18) **não são usados** no few-shot nem no guia de estilo dinâmico. Continuam na pasta, mas são ignorados (ver log: `ignorado para few-shot`).

## Biblioteca vazia

Se não houver nenhum `.md` elegível, a IA usa um **guia de estilo mínimo** embutido no código (`GUIA_ESTILO_PADRAO_DEBENTURES` em `biblioteca.py`), sem exemplos — zero ruído de outros programas.

## Feedbacks

`feedbacks/feedbacks.jsonl` regista avaliações da equipa (pode ficar vazio no início).
