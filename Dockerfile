# Usa imagem base Python leve
FROM python:3.13-slim 

ARG POETRY_VERSION=2.1.3
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_HOME="/usr/local" \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="${POETRY_HOME}/bin:${PATH}"

# Configura diretório de trabalho
WORKDIR /app

# Instala dependências de sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copia todo o código da app
COPY . /app

# Defina as variáveis de ambiente em tempo de build (podem ser sobrepostas em tempo de execução)
ENV PYTHONUNBUFFERED=1

# Comando padrão (ajuste para seu entrypoint)
CMD ["python", "-m", "application.main"]
