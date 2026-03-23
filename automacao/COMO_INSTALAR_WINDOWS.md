# Como instalar o sistema no Windows

**Sistema:** Parecer de Mérito — **Debêntures Incentivadas** / MCID  
**Porta do app:** `8502` (o Pro-Cidades, se existir na mesma máquina, costuma usar `8501`)  
**Tempo estimado:** 20 a 40 minutos (a maior parte é o download do modelo de IA ~5 GB)

---

## Resumo do que será instalado

| Componente | Para que serve | Tamanho |
|---|---|---|
| **Python 3.11+** | Linguagem que roda o sistema | ~30 MB |
| **Ollama** | Motor de IA local (privado, offline) | ~60 MB |
| **qwen2.5:7b** | Modelo de linguagem para gerar pareceres | ~5 GB |
| **Dependências Python** | Bibliotecas do sistema | ~300 MB |

---

## PASSO 1 — Copiar os arquivos do sistema

### Opção A — Pen drive ou rede

1. Copie a pasta **`Sistema_Debentures`** (ou pelo menos **`Sistema_Debentures/automacao`**) para o PC Windows.
2. Exemplo de destino:  
   `C:\Users\[nome]\Documents\MCID\Sistema_Debentures\automacao`

> A pasta `biblioteca/pareceres_validados/` pode começar vazia; a equipe adiciona pareceres validados conforme o uso.

### Opção B — GitHub

```
git clone https://github.com/victorpeborges-ADS/MCID.git
cd MCID\Sistema_Debentures\automacao
```

*(Ajuste o caminho se o repositório usar outro nome de pasta.)*

---

## PASSO 2 — Instalar o Python

1. Acesse: **https://www.python.org/downloads/**
2. Clique em **"Download Python 3.11"** (ou versão mais recente)
3. Execute o instalador
4. **OBRIGATÓRIO:** Na primeira tela, marque ✅ **"Add Python to PATH"**
5. Clique em **"Install Now"**
6. Aguarde e feche

---

## PASSO 3 — Executar o instalador automático

1. Abra a pasta `automacao` no Windows
2. Clique duas vezes em **`instalar_windows.bat`**
3. Se aparecer aviso do Windows Defender:  
   → Clique em **"Mais informações"** → **"Executar assim mesmo"**

O instalador irá automaticamente:
- ✅ Verificar o Python
- ✅ Baixar e instalar o **Ollama** (se não estiver instalado)
- ✅ Criar o ambiente Python isolado
- ✅ Instalar todas as dependências
- ✅ Baixar o modelo de IA **qwen2.5:7b** (~5 GB — pode demorar 20–30 min)
- ✅ Criar atalho na Área de Trabalho (**Debêntures Incentivadas MCID**)

> **Não feche a janela** durante a instalação, especialmente durante o download do modelo.

---

## PASSO 4 — Configurar a senha do sistema

1. Na pasta `automacao`, abra a pasta **`.streamlit`**  
   (se não aparecer, ative "Mostrar itens ocultos" no Explorador de Arquivos → guia Exibir → marcar "Itens ocultos")
2. Abra o arquivo **`secrets.toml`** com o Bloco de Notas
3. Na linha `app_password`, coloque a senha da equipe:
   ```
   app_password = "senha-combinada-com-a-equipe"
   ```
4. Salve o arquivo

---

## PASSO 5 — Usar o sistema

1. Clique duas vezes no atalho **"Debêntures Incentivadas MCID"** na Área de Trabalho
2. Uma janela preta abrirá (é o servidor — não feche)
3. O navegador abrirá automaticamente em **`http://localhost:8502`**
4. Digite a senha quando solicitado
5. Selecione o provedor **Ollama** e o modelo **qwen2.5:7b**

---

## Configuração de provedores de IA em nuvem (opcional)

O Ollama roda localmente e não precisa de internet. Se quiser também usar provedores em nuvem (Groq, Mistral AI) para comparação ou quando o Ollama estiver lento:

### Groq (gratuito)
1. Crie conta em: **https://console.groq.com**
2. Menu "API Keys" → "Create API Key" → copie a chave `gsk_...`
3. No arquivo `.streamlit\secrets.toml`, preencha:
   ```
   groq_api_key = "gsk_sua_chave_aqui"
   ```

### Mistral AI
1. Crie conta em: **https://console.mistral.ai**
2. "API Keys" → "Create new key" → copie
3. No arquivo `.streamlit\secrets.toml`, preencha:
   ```
   mistral_api_key = "sua_chave_aqui"
   ```

---

## Como receber atualizações automáticas pelo GitHub

Sempre que o responsável publicar melhorias, você atualiza em segundos — sem pen drive.

### Pré-requisito: instalar o Git (uma única vez)

1. Acesse: **https://git-scm.com/download/win**
2. Clique em "Click here to download" (versão mais recente)
3. Execute o instalador e mantenha todas as opções padrão
4. Reinicie o computador

### Para receber uma atualização

1. Abra a pasta `automacao`
2. Clique duas vezes em **`atualizar_windows.bat`**
3. O script mostra o que vai mudar e pede confirmação
4. Confirme com **S** — leva menos de 1 minuto
5. Suas credenciais (senha e chaves de API) são preservadas automaticamente

> O script atualiza apenas os arquivos do sistema. **Nunca sobrescreve o `secrets.toml`.**

> **Atualização a partir de março/2026:** o `atualizar_windows.bat` tenta automaticamente guardar em *stash* ficheiros locais não rastreados que bloqueiem o merge. Se ainda falhar, use a solução manual abaixo.

### Fluxo de trabalho da equipe

```
Responsável MCID (Mac)           Colega (Windows)
──────────────────────────────   ──────────────────────────────
1. Melhora o sistema
2. git push → GitHub        →    GitHub guarda a versão nova

                                 3. Clica em atualizar_windows.bat
                                 4. Sistema atualizado em < 1 min ✅
```

---

## Requisitos de hardware

| Requisito | Mínimo | Recomendado |
|---|---|---|
| RAM | 16 GB | 16 GB ou mais |
| Espaço em disco | 8 GB livres | 15 GB livres |
| CPU | Qualquer moderno | Intel i5/i7 ou AMD Ryzen |
| GPU | Não necessária | NVIDIA acelera a IA |
| Internet | Para instalação | Não necessária após instalar |

> Com 16 GB de RAM e sem GPU, o modelo qwen2.5:7b gera uma análise em **5 a 15 minutos**.  
> Com Groq ou Mistral AI (nuvem), a análise leva **30 a 60 segundos**.

---

## Problemas comuns

### "Python não reconhecido como comando"
Desinstale o Python e reinstale marcando **"Add Python to PATH"**.

### "Não foi possível baixar o Ollama automaticamente"
Acesse **https://ollama.com/download** e baixe manualmente. Execute o instalador e reinicie o computador. Depois execute `instalar_windows.bat` novamente.

### Download do modelo muito lento
Deixe rodando e vá fazer outra coisa. O modelo (~5 GB) precisa ser baixado apenas uma vez.

### O navegador não abre automaticamente
Abra manualmente e acesse: **http://localhost:8502**

### Ollama não inicia ao abrir o sistema
Procure o ícone do Ollama na bandeja do sistema (canto inferior direito) e clique para iniciar. Se não aparecer, abra pelo menu Iniciar.

### Análise trava ou demora muito
- Com Ollama: normal em CPU — pode levar 15 minutos. Não feche o navegador.
- Mude para Groq (gratuito) na barra lateral do sistema para análises mais rápidas.

### Erro: *"untracked working tree files would be overwritten by merge"*
Significa que existem **ficheiros na pasta que o Git não controla** (cópias antigas ou ficheiros criados à mão) com o **mesmo nome** que o GitHub vai trazer na atualização. O Git aborta para não apagar o conteúdo local sem aviso.

**Opção A — na linha de comando** (na **raiz** da pasta do projeto, onde está a pasta `automacao`):

```bat
git stash push -u -m "backup-antes-atualizar"
git merge --ff-only origin/main
```

Depois, se não precisar do que ficou no *stash*: `git stash drop`.

**Opção B — apagar ou renomear só os ficheiros citados no erro** (ex.: `.cursorignore`, `automacao\repositorio_portarias.py`) e voltar a executar `atualizar_windows.bat`. Se forem só duplicados do repositório, pode apagar com segurança e deixar o Git trazer a versão oficial.

---

## Estrutura dos arquivos após instalação

```
automacao/
├── app.py                      ← código principal do sistema
├── branding.py                 ← textos e identidade Debêntures
├── motor.py                    ← motor de análise e geração
├── fontes_publicas.py          ← coleta dados IBGE, CAPAG, etc.
├── biblioteca.py               ← gerencia pareceres de referência
├── llm_client.py               ← conecta com os provedores de IA
├── requirements.txt            ← lista de dependências
├── instalar_windows.bat        ← instalador (executar uma vez)
├── iniciar_windows.bat         ← iniciar o sistema (usar sempre)
├── atualizar_windows.bat       ← busca atualizações do GitHub
├── COMO_INSTALAR_WINDOWS.md    ← este guia
├── meu_ambiente/               ← ambiente Python (criado pelo instalador)
├── .streamlit/
│   ├── secrets.toml            ← senha e chaves de API
│   └── secrets.toml.example    ← modelo para preencher
└── biblioteca/
    ├── pareceres_validados/    ← pareceres aprovados (referência de estilo)
    └── feedbacks/              ← registro de feedbacks da equipe
```

---

*Sistema Debêntures Incentivadas v1.0 — MCID*
