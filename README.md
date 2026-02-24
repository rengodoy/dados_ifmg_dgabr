# Repositório auxiliar para a dissertação de mestrado

### Estrutura do Repositório

```text
.
├── dados_ifmg_ckan/       # Dados brutos extraídos (organizados por ID)
├── download_ckan.py       # Script principal de extração
├── DGABr_IFMG_Final.xlsx  # Planilha com os resultados consolidados da análise
├── pyproject.toml         # Definição de dependências (gerenciado pelo uv)
└── .env_example           # Modelo para configuração do ambiente

## Para rodar o script seguem as instruções

### Pré-requisitos
- uv
- Python `>=3.14`
- Dependências do projeto instaladas (veja `pyproject.toml`).

### Configuração

O script utiliza variáveis de ambiente para configuração. Crie um arquivo `.env` na raiz do projeto (baseado no `.env_example`) e ajuste conforme necessário:

```bash
cp .env_example .env
```

As variáveis disponíveis são:

- `CKAN_BASE_URL`: URL base da instância CKAN (padrão: `https://dadosabertos.ifmg.edu.br`)
- `CKAN_OUTPUT_DIR`: Diretório onde os dados serão salvos
- `CKAN_HTTP_TIMEOUT`: Timeout para requisições HTTP
- `CKAN_DOWNLOAD_TIMEOUT`: Timeout específico para download de arquivos
- `CKAN_RETRIES`: Número de tentativas em caso de falha
- `CKAN_BACKOFF_BASE`: Base para cálculo do backoff exponencial

### Uso

Para executar o script de download e coleta de dados do CKAN:

```bash
uv run download_ckan.py
```

O script irá:
1. Conectar à API do CKAN definida.
2. Listar todos os conjuntos de dados (packages).
3. Baixar metadados (`metadata.json`) e recursos (arquivos de dados) para cada dataset.
4. Organizar os arquivos em pastas por ID do dataset dentro de `CKAN_OUTPUT_DIR`.
5. Gerar um relatório de status dos downloads (`resource_status.json`).
 
