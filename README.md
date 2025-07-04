# Email-Metrics 📊  

[![Python](https://img.shields.io/badge/python-3.13+-blue?logo=python)](https://www.python.org/)　
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)　
[![Microsoft Graph](https://img.shields.io/badge/Microsoft%20Graph-API-blue?logo=microsoft)](https://learn.microsoft.com/graph)　
[![Metabase](https://img.shields.io/badge/Metabase-0.49-blue?logo=metabase)](https://github.com/metabase/metabase)  
[![License](https://img.shields.io/badge/license-GNU-green)](#license)

> Coleta métricas de campanhas de e-mail via **Microsoft Graph**, grava em **PostgreSQL**
> e oferece consultas prontas para **Metabase** – com logs estruturados para observabilidade.

---

## Índice <!-- GitHub gera as âncoras -->
1. [Visão geral](#visão-geral)  
2. [Fluxo de funcionamento](#fluxo-de-funcionamento)  
3. [Banco & Modelo de dados](#banco-e-modelo-de-dados)  
4. [Estrutura de diretórios](#estrutura-de-diretórios)  
5. [Variáveis de ambiente](#variáveis-de-ambiente)  
6. [Execução rápida](#execução-rápida)  
7. [Modo leigo × Modo técnico](#modo-leigo--x--modo-técnico)  
8. [Consultas para dashboards](#consultas-para-dashboards)  
9. [Roadmap / TODO](#roadmap--todo)  
10. [Contribuição](#contribuição)  
11. [Licença](#license)  

---

## Visão geral

| Componente                | Responsabilidade |
|---------------------------|------------------|
| **GraphApiClient**        | Paginação segura + retries contra Graph API. |
| **EmailMetricsService**   | Detecta *bounce* / *reply* por conversa e classifica a “temperatura” <br>• **quente** = replied  • **morno** = entregue sem reply  • **frio** = bounce |
| **PgEmailRepository**     | UPSERT em `emails` e INSERT append-only em `metrics`. |
| **FetchAndStoreMetrics**  | Orquestra para **N** contas simultâneas. |
| **Structlog**             | JSON logs prontos para Loki / ELK. |
| **Metabase (opcional)**   | Dashboards plug-and-play via docker-compose. |

---

## Fluxo de funcionamento

```mermaid
sequenceDiagram
    autonumber
    participant Cron as CronScheduler
    participant UseCase as FetchAndStoreMetrics
    participant Graph as Microsoft Graph
    participant Repo as PgEmailRepository
    Cron->>UseCase: job.execute()
    UseCase->>Graph: fetch_mail_folders()
    UseCase->>Graph: fetch_messages_in_folder()
    UseCase->>UseCase: calcular métricas (bounce/reply)<br/>classificar temperatura
    UseCase->>Repo: save_all(emails)  (UPSERT)
    UseCase->>Repo: save(metrics)     (INSERT)
````

---

## Banco e Modelo de dados

### 1. accounts

| coluna          | tipo          | descrição                 |
| --------------- | ------------- | ------------------------- |
| `id`            | `uuid` PK     | Gerado ao cadastrar conta |
| `email_address` | `text` UNIQUE |                           |

### 2. emails (row-level)

| campo                 | tipo                           | observação             |
| --------------------- | ------------------------------ | ---------------------- |
| `recipient_addresses` | `text[]`                       | todos os destinatários |
| `temperature_label`   | `text` (quente / morno / frio) |                        |
| `temperature_pct`     | `int` ×10000 (0, 5000, 10000)  |                        |

Chave única = `(account_id, message_id, conversation_id)`.

### 3. metrics (snapshot diário)

| clean                                | raw                         | ...                         |
| ------------------------------------ | --------------------------- | --------------------------- |
| `total_*` – filtrados e deduplicados | `raw_total_*` – visão bruta | `temperature_*` da campanha |

BRIN index em `(account_id, run_at)` garante leitura rápida por período.

---

## Estrutura de diretórios

```
.
├── adapters/           # integrações externas (Graph, SQL, cron)
├── application/        # casos de uso orquestradores
├── domain/             # entidades + regras de negócio
├── ports/              # interfaces (hexagonal)
├── config/             # .env, logging, settings
├── infrastructure/     # docker-compose, metabase, migrations
└── tests/
```

---

## Variáveis de ambiente

| chave                                   | exemplo / default                           |
| --------------------------------------- | ------------------------------------------- |
| **OAuth / Graph**                       |                                             |
| `TENANT_ID` `CLIENT_ID` `CLIENT_SECRET` | credenciais do app registration             |
| `EMAIL_ACCOUNTS`                        | `marketing@acme.com,suporte@acme.com`       |
| **Filtros**                             |                                             |
| `SUBJECT_FILTER`                        | `OPORTUNIDADE DE ACORDO,PROPOSTA DE ACORDO` |
| `IGNORED_RECIPIENT_PATTERNS`            | `@spam,@test`                               |
| `SENT_FOLDER_NAME`                      | `itens enviados`                            |
| **PostgreSQL**                          |                                             |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD`   | idem docker-compose                         |
| **Extra**                               |                                             |
| `BULK_CHUNK_SIZE`                       | batch UPSERT (default = 300)                |

---

## Execução rápida

### Docker Compose (recomendado)

```bash
cp .env.example .env   # edite credenciais
docker compose up --build   # inclui Metabase em :3878
```

* Logs estruturados em stdout.
* Metabase inicializa com banco `metabase` dentro do mesmo PostgreSQL.

### Execução única (Poetry)

```bash
poetry install
poetry run python -m application.main --once
```

---

## Modo leigo × Modo técnico

| 💬 Leigo                                                                                          | 🛠️ Técnico                                                                       |
| ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| O robô abre a caixa “Itens enviados”, conta quem recebeu, quem respondeu e quem voltou como erro. | Chamada à Graph API (`/messages?$filter=conversationId…`) e análise de cabeçalho. |
| Grava tudo num banco para ver histórico.                                                          | UPSERT em `emails`, INSERT em `metrics`, índices BRIN.                            |
| Classifica cada contato em quente, morno ou frio.                                                 | `temperature_label` via flags `is_replied / is_bounced`.                          |

---

## Consultas para dashboards

```sql
-- KPI diário por conta
SELECT a.email_address AS "Conta",
       m.date, m.total_sent, m.total_delivered,
       ROUND(m.delivery_rate/100.0,2) AS "Delivery (%)",
       ROUND(m.reply_rate/100.0,2)    AS "Reply (%)",
       m.temperature_label
FROM   public.metrics m
JOIN   public.accounts a ON a.id = m.account_id
ORDER  BY m.date DESC;

-- Distribuição de temperatura dos e-mails (última execução)
SELECT temperature_label AS "Temperatura", COUNT(*) AS "E-mails"
FROM   public.emails e
WHERE  sent_datetime >= (SELECT MAX(run_at) FROM metrics) - INTERVAL '1 hour'
GROUP  BY 1;
```

> Mais exemplos na pasta [`docs/sql/`](./docs/sql/).

---

## License

GNU © 2025 – use, modifique e compartilhe.
