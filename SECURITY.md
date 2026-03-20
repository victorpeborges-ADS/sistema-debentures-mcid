# Segurança

## Reportar vulnerabilidades

Para questões **sensíveis** (credenciais expostas, falhas que permitam acesso indevido, etc.), use os [GitHub Security Advisories](https://github.com/victorpeborges-ADS/sistema-debentures-mcid/security/advisories/new) deste repositório, para comunicação privada com os mantenedores.

Para bugs gerais ou melhorias, abra uma [issue](https://github.com/victorpeborges-ADS/sistema-debentures-mcid/issues) pública.

## Boas práticas no deploy

- Não commite `automacao/.streamlit/secrets.toml` nem ficheiros `.env` com chaves reais (já estão no `.gitignore`).
- Em produção, defina `APP_PASSWORD` ou `secrets.toml` apenas no servidor.
- Restrinja o acesso à rede (intranet / VPN) quando o sistema tratar dados institucionais.
