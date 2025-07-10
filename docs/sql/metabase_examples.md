### **Dashboard Completo de Métricas de E-mail**

\<p align="right"\>
\<a href="../../README.md"\>⬅️ Voltar para o README\</a\>
\</p\>

Aqui estão 14 KPIs para uma visão 360° da sua operação de e-mail, com foco em snapshots de performance, análise de tendências temporais e diagnósticos operacionais.

-----

### **Seção 1: Painel de Performance (Snapshot)**

*Visão geral do desempenho mais recente.*

#### **KPI 1: Resumo de Performance Diária por Conta (Corrigido)**

Visão geral dos resultados de cada conta, mostrando sempre a medição mais recente para cada dia.

> **Visualização:** Tabela.

```sql
-- Seleciona APENAS a medição mais recente de cada conta para cada dia
SELECT DISTINCT ON (a.email_address, m.date)
    a.email_address                                                       AS "Conta",
    m.date                                                                AS "Data",
    m.total_sent                                                          AS "Enviados (Líquido)",
    m.total_delivered                                                     AS "Entregues",
    m.total_replied                                                       AS "Respostas",
    m.total_bounced                                                       AS "Bounces",
    ROUND(m.reply_rate / 100.0, 2)                                        AS "Taxa de Resposta (%)",
    m.temperature_label                                                   AS "Temp. da Campanha",
    TO_CHAR((m.avg_reply_latency_sec || ' second')::interval, 'HH24:MI:SS') AS "Latência Média de Resposta"
FROM
    public.metrics m
JOIN
    public.accounts a ON m.account_id = a.id
ORDER BY
    a.email_address, m.date, m.run_at DESC;
```

-----

#### **KPI 2: Funil de Engajamento do Dia (por Conta)**

Painel de performance do dia para cada conta, com taxas de entrega e resposta para uma análise rápida.

> **Visualização:** Tabela.

```sql
-- Funil de performance de hoje para cada conta, com taxas
SELECT
    a.email_address AS "Conta",
    COUNT(e.id) AS "Enviados (Líquido)",
    SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END) AS "Entregues",
    SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END) AS "Respondidos",
    ROUND(100.0 * SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END) / NULLIF(COUNT(e.id), 0), 2) AS "Taxa de Entrega (%)",
    ROUND(100.0 * SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END), 0), 2) AS "Taxa de Resposta (%)"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.sent_datetime >= DATE_TRUNC('day', NOW() AT TIME ZONE 'America/Sao_Paulo')
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY
    a.email_address
ORDER BY
    "Respondidos" DESC;
```

-----

#### **KPI 3: Ranking de Performance por Conta**

Um índice claro para ranquear as contas, combinando a taxa de resposta com a qualidade (pontuação) dessas respostas.

> **Visualização:** Tabela.

```sql
-- Ranking de contas por um índice de performance (taxa de resposta * pontuação média)
SELECT
    a.email_address AS "Conta",
    ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0), 2) AS "Taxa de Resposta (%)",
    ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média",
    ROUND((SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0)) * AVG(e.engagement_score), 2) AS "Índice de Performance"
FROM
    public.emails e
JOIN
    public.accounts a ON a.id = e.account_id
WHERE
    e.sent_datetime >= CURRENT_DATE - INTERVAL '30 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY
    a.email_address
ORDER BY
    "Índice de Performance" DESC;
```

-----

### **Seção 2: Evolução Temporal e Tendências**

*Acompanhe a performance ao longo do tempo para identificar padrões e melhorias.*

#### **KPI 4: Evolução da Taxa de Resposta e Entrega (Novo)**

Acompanhe as duas taxas mais importantes, semana a semana, para entender a saúde geral da sua operação por conta.

> **Visualização:** Gráfico de Linhas (Eixo X: "Semana", Eixo Y: Taxas, Separar por: "Conta").

```sql
-- Evolução semanal da Taxa de Entrega e Taxa de Resposta por conta
SELECT
    DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana",
    a.email_address AS "Conta",
    ROUND(100.0 * SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END) / NULLIF(COUNT(e.id), 0), 2) AS "Taxa de Entrega (%)",
    ROUND(100.0 * SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END), 0), 2) AS "Taxa de Resposta (%)"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
    -- ⚠️ Mantenha esta lista de prefixos sincronizada com a configuração da sua aplicação!
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' AND e.subject NOT ILIKE 'Automatic reply:%'
GROUP BY "Semana", "Conta"
ORDER BY "Semana" ASC, "Conta";
```

-----

#### **KPI 5: Evolução da Latência Média de Resposta (Novo)**

Monitore se o tempo para obter respostas está diminuindo (bom) ou aumentando (ruim) ao longo do tempo.

> **Visualização:** Gráfico de Linhas (Eixo X: "Semana", Eixo Y: Latência Média, Separar por: "Conta").

```sql
-- Evolução do tempo médio de resposta por conta
SELECT
    DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana",
    a.email_address AS "Conta",
    AVG(e.reply_latency_sec) / 3600 AS "Latência Média (em horas)",
    COUNT(e.id) AS "Nº de Respostas"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.is_replied = true
    AND e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY "Semana", "Conta"
ORDER BY "Semana" ASC, "Conta";
```

-----

#### **KPI 6: Evolução da Pontuação Média de Engajamento (Novo)**

A métrica definitiva de *qualidade* do engajamento. Uma pontuação crescente indica respostas mais rápidas e eficazes.

> **Visualização:** Gráfico de Linhas (Eixo X: "Semana", Eixo Y: Pontuação, Separar por: "Conta").

```sql
-- A qualidade do engajamento está melhorando ou piorando?
SELECT
    DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana",
    a.email_address AS "Conta",
    ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média de Engajamento"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY "Semana", "Conta"
ORDER BY "Semana" ASC, "Conta";
```

-----

### **Seção 3: Análise de Engajamento e Conteúdo**

*Mergulhe nos detalhes do que funciona e como os clientes se comportam.*

#### **KPI 7: Análise de Pontuação de Engajamento (por Conta)**

Entenda a distribuição das pontuações dos e-mails respondidos para comparar a qualidade do engajamento entre contas.

> **Visualização:** Tabela ou Gráfico de Barras.

```sql
-- Distribuição de pontuação por conta para e-mails que receberam resposta
SELECT
    a.email_address AS "Conta",
    e.engagement_score AS "Pontuação",
    COUNT(*) AS "Total de Respostas",
    TO_CHAR((AVG(e.reply_latency_sec) || ' second')::interval, 'DD"d "HH24:MI:SS') AS "Latência Média"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.is_replied = true
    AND e.sent_datetime >= CURRENT_DATE - INTERVAL '30 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY
    a.email_address, e.engagement_score
ORDER BY
    a.email_address, e.engagement_score DESC;
```

-----

#### **KPI 8: Top 20 Assuntos por Pontuação de Engajamento**

Identifica os assuntos que geram as respostas mais valiosas (rápidas e efetivas).

> **Visualização:** Tabela.

```sql
-- Assuntos que geram as respostas mais valiosas (rápidas)
SELECT
    e.subject AS "Assunto",
    COUNT(*) AS "Enviados",
    SUM(e.is_replied::int) AS "Respostas",
    ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(COUNT(*), 0), 2) AS "Taxa de Resposta (%)",
    ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média"
FROM
    public.emails e
WHERE
    e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
    AND e.is_bounced IS FALSE
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY e.subject
HAVING COUNT(*) >= 20 -- Apenas assuntos com um volume mínimo
ORDER BY "Pontuação Média" DESC, "Taxa de Resposta (%)" DESC
LIMIT 20;
```

-----

#### **KPI 9: Distribuição da Latência de Resposta (com Percentual)**

Entenda *quando* os clientes respondem, ajudando a alinhar expectativas e otimizar follow-ups.

> **Visualização:** Gráfico de Pizza ou Barras.

```sql
-- Em quanto tempo as respostas chegam? (com percentual)
WITH latency_counts AS (
    SELECT
        CASE
            WHEN reply_latency_sec < 3600 THEN '01. Em menos de 1 hora'
            WHEN reply_latency_sec < 14400 THEN '02. Entre 1 e 4 horas'
            WHEN reply_latency_sec < 43200 THEN '03. Entre 4 e 12 horas'
            WHEN reply_latency_sec < 86400 THEN '04. Entre 12 e 24 horas'
            WHEN reply_latency_sec < 172800 THEN '05. Entre 24 e 48 horas'
            ELSE '06. Mais de 48 horas'
        END AS "Faixa de Latência",
        COUNT(*) AS "Total de Respostas"
    FROM public.emails
    WHERE is_replied = true AND sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY "Faixa de Latência"
)
SELECT
    "Faixa de Latência",
    "Total de Respostas",
    ROUND(100.0 * "Total de Respostas" / SUM("Total de Respostas") OVER(), 2) AS "Percentual (%)"
FROM latency_counts
ORDER BY "Faixa de Latência";
```

-----

### **Seção 4: Saúde da Operação e Diagnósticos**

*Métricas para identificar e corrigir problemas de entrega e reputação.*

#### **KPI 10: Mapa de Calor de Engajamento por Hora do Dia**

Revela os melhores horários para enviar e-mails com base na pontuação média, não apenas no volume.

> **Visualização:** Mapa de Calor (Heatmap).

```sql
-- Média de engagement_score por hora do dia e dia da semana
SELECT
    EXTRACT(hour FROM sent_datetime AT TIME ZONE 'America/Sao_Paulo') AS "Hora do Dia",
    TO_CHAR(sent_datetime AT TIME ZONE 'America/Sao_Paulo', 'ID - Day') AS "Dia da Semana",
    ROUND(AVG(engagement_score)) AS "Pontuação Média de Engajamento"
FROM
    public.emails e
WHERE
    sent_datetime >= CURRENT_DATE - INTERVAL '28 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY 1, 2
ORDER BY 2, 1;
```

-----

#### **KPI 11: Diagnóstico de Bounces por Domínio**

Identifica problemas de entrega com domínios específicos (ex: bloqueios de servidor).

> **Visualização:** Tabela.

```sql
-- Domínios com maior número de bounces
SELECT
    SUBSTRING(recipient FROM '@(.*)$') AS "Domínio do Destinatário",
    COUNT(*) AS "Total de Bounces"
FROM (
    SELECT unnest(recipient_addresses) AS recipient
    FROM public.emails
    WHERE is_bounced = TRUE AND sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
) AS unnested_emails
GROUP BY 1
HAVING COUNT(*) > 5 -- Apenas domínios com falhas recorrentes
ORDER BY "Total de Bounces" DESC
LIMIT 25;
```

-----

#### **KPI 12: Comparativo de Temperatura por Conta (Percentual)**

Visão percentual da distribuição de temperatura para comparar o perfil de engajamento entre contas.

> **Visualização:** Gráfico de Barras Empilhadas (100%).

```sql
-- Distribuição percentual de temperatura por conta
SELECT
    a.email_address AS "Conta",
    ROUND(100.0 * SUM((e.temperature_label = 'quente')::int) / COUNT(*), 1) AS "% Quente",
    ROUND(100.0 * SUM((e.temperature_label = 'morno')::int) / COUNT(*), 1) AS "% Morno",
    ROUND(100.0 * SUM((e.temperature_label = 'frio')::int) / COUNT(*), 1)  AS "% Frio",
    COUNT(*) AS "Total de Envios (Líquido)"
FROM
    public.emails e
JOIN
    public.accounts a ON a.id = e.account_id
WHERE
    e.sent_datetime >= CURRENT_DATE - INTERVAL '30 days'
    AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%'
GROUP BY a.email_address
ORDER BY "% Quente" DESC;
```

-----

#### **KPI 13 & 14: Listas de Diagnóstico (com mais Contexto)**

Consultas para encontrar os principais ofensores de bounce e os destinatários mais engajados.

> **Visualização:** Tabela.

```sql
-- KPI 13: Top 30 Destinatários com mais Bounces (com contexto)
SELECT
    unnest(e.recipient_addresses) AS "Destinatário",
    COUNT(*) AS "Total de Bounces",
    STRING_AGG(DISTINCT a.email_address, ', ') AS "Contas de Origem",
    MAX(e.sent_datetime)::date AS "Data do Último Bounce"
FROM
    public.emails e
JOIN
    public.accounts a ON e.account_id = a.id
WHERE
    e.is_bounced IS TRUE AND e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

-- KPI 14: Top 30 Destinatários mais Engajados (com pontuação média)
SELECT
    unnest(e.recipient_addresses) AS "Destinatário",
    SUM(e.engagement_score) AS "Pontuação Total",
    ROUND(AVG(e.engagement_score), 1) AS "Pontuação Média",
    COUNT(*) AS "E-mails Respondidos"
FROM
    public.emails e
WHERE
    e.is_replied = TRUE AND e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
```