# Configurar Azure OpenAI no sistema

Ninguém pode “extrair” a chave por ti sem acesso ao **Portal Azure** da tua organização ou subscrição. Este guia diz **onde** obter cada valor e **como** colocá-los no projeto.

## O que vais precisar (três valores)

| Campo no sistema | Onde obter no Azure |
|------------------|---------------------|
| **Endpoint** | Recurso Azure OpenAI → **Keys and Endpoint** → *Endpoint* (`https://NOME.openai.azure.com/`) |
| **API Key** | Mesmo ecrã → **KEY 1** ou **KEY 2** |
| **Nome do Deployment** | **Azure OpenAI Studio** (ou Foundry) → **Deployments** → nome que deste ao deployment (não é o nome técnico do modelo sozinho) |

Documentação oficial Microsoft: [Criar e implementar um recurso Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource).

## Passos resumidos (portal)

1. Entra em [portal.azure.com](https://portal.azure.com) com conta que tenha permissão na subscrição.
2. Abre o recurso **Azure OpenAI** (serviço de IA / Cognitive Services).
3. **Keys and Endpoint** → copia **Endpoint** e uma **Key**.
4. Abre o **Azure OpenAI Studio** (link no recurso) → **Deployments** → cria um deployment (ex.: modelo `gpt-4o` ou `gpt-4o-mini`) e **anota o nome** que escolheste.

Se não vês “Azure OpenAI” ou dá erro de quota/região, a **TI** ou o administrador da subscrição tem de criar o recurso ou aprovar modelos.

## Colocar no projeto

### Opção A — `secrets.toml` (recomendado em equipa)

1. Copia `automacao/.streamlit/secrets.toml.example` para `automacao/.streamlit/secrets.toml`.
2. Preenche:

```toml
azure_openai_api_key = "cole-a-key-aqui"
azure_openai_endpoint = "https://SEU-RECURSO.openai.azure.com/"
azure_openai_deployment = "nome-do-deployment"
```

3. Reinicia o Streamlit. Na barra lateral, escolhe **Azure OpenAI** — os campos podem vir já preenchidos a partir destes valores.

### Opção B — variáveis de ambiente (servidor / CI)

Definir antes de iniciar o Streamlit:

```bash
export AZURE_OPENAI_ENDPOINT="https://SEU-RECURSO.openai.azure.com/"
export AZURE_OPENAI_API_KEY="sua-key"
export AZURE_OPENAI_DEPLOYMENT="nome-do-deployment"
```

No Windows (CMD): `set AZURE_OPENAI_ENDPOINT=...` (sessão atual).

## Testar

Na barra lateral: **Testar conexão**. Se falhar, confirma:

- Endpoint **sem** path extra (só a URL base do recurso).
- Deployment **exatamente** igual ao nome no portal.
- Modelo do deployment compatível com chat (ex.: `gpt-4o`, `gpt-4o-mini`).

## Segurança

- Não commits `secrets.toml` nem chaves em repositório público.
- Rotação: no portal podes regenerar KEY 1/2 e atualizar o `secrets.toml`.
