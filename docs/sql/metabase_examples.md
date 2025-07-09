### **Dashboard Completo de Métricas de E-mail**

Aqui estão 12 KPIs para uma visão 360° da sua operação de e-mail.

#### **Seção 1: Visão Geral e Performance Agregada**

-----

#### **KPI 1: Resumo de Performance Diária por Conta (Otimizado)**

Visão geral dos resultados de cada conta para um dia específico. Adicionamos a latência média de resposta para uma análise mais profunda do engajamento.

> **Visualização:** Tabela.

```sql
-- Resumo de performance diária por conta, incluindo latência média de resposta.
SELECT
  a.email_address                                             AS "Conta",
  m.date                                                      AS "Data",
  m.total_sent                                                AS "Enviados (Líquido)",
  m.total_delivered                                           AS "Entregues",
  m.total_replied                                             AS "Respostas",
  m.total_bounced                                             AS "Bounces",
  ROUND(m.reply_rate / 100.0, 2)                              AS "Taxa de Resposta (%)",
  m.temperature_label                                         AS "Temp. da Campanha",
  -- Converte a latência de segundos para um formato mais legível
  TO_CHAR((m.avg_reply_latency_sec || ' second')::interval, 'HH24:MI:SS') AS "Latência Média de Resposta"
FROM
  public.metrics m
JOIN
  public.accounts a ON m.account_id = a.id
-- [[ WHERE {{data}} ]] -- Filtro opcional para o dashboard
ORDER BY
  m.date DESC, a.email_address;
```

-----

#### **KPI 2: Evolução das Taxas de Engajamento (Otimizado)**

Acompanhe a saúde da entregabilidade e do engajamento ao longo do tempo. A consulta agora calcula a taxa real diária, em vez de uma média de médias.

> **Visualização:** Gráfico de Linha com duas séries (Taxa de Entrega, Taxa de Resposta).

```sql
-- Evolução da performance geral nos últimos 30 dias.
SELECT
  m.date                                                                  AS "Data",
  -- Calcula a taxa de entrega real do dia somando os totais de todas as contas
  ROUND(100.0 * SUM(m.total_delivered) / NULLIF(SUM(m.total_sent), 0), 2)  AS "Taxa de Entrega (%)",
  -- Calcula a taxa de resposta real do dia
  ROUND(100.0 * SUM(m.total_replied) / NULLIF(SUM(m.total_delivered), 0), 2) AS "Taxa de Resposta (%)"
FROM
  public.metrics m
WHERE
  m.date >= CURRENT_DATE - INTERVAL '30 days' -- Ajuste o período conforme necessário
GROUP BY
  m.date
ORDER BY
  m.date;
```

-----

#### **KPI 3: Funil de Engajamento do Dia (Novo)**

Uma visão macro do funil de interações para o dia corrente, ideal para o topo do dashboard.

> **Visualização:** Funil ou Cartões com "Número Grande".

```sql
-- Funil de engajamento para os e-mails enviados hoje (considerando o fuso de Londrina)
SELECT
  COUNT(*)                                    AS "1. E-mails Enviados",
  SUM(CASE WHEN NOT is_bounced THEN 1 ELSE 0 END) AS "2. E-mails Entregues",
  SUM(CASE WHEN is_replied THEN 1 ELSE 0 END)     AS "3. E-mails Respondidos"
FROM
  public.emails
WHERE
  sent_datetime >= DATE_TRUNC('day', NOW() AT TIME ZONE 'America/Sao_Paulo');
```

-----

#### **Seção 2: Análise de Engajamento e Conteúdo**

-----

#### **KPI 4: Análise de Pontuação de Engajamento (Novo)**

Entenda a distribuição das pontuações dos e-mails respondidos. Essencial para ver o impacto dos bônus de latência.

> **Visualização:** Gráfico de Barras ou Tabela.

```sql
-- Distribuição de pontuação para e-mails que receberam resposta
SELECT
  engagement_score                                                        AS "Pontuação",
  COUNT(*)                                                                AS "Total de E-mails",
  -- Formata a latência média para o formato "dias hh:mm:ss"
  TO_CHAR((AVG(reply_latency_sec) || ' second')::interval, 'DD"d "HH24:MI:SS') AS "Latência Média"
FROM
  public.emails
WHERE
  is_replied = true AND sent_datetime >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  engagement_score
ORDER BY
  engagement_score DESC;
```

-----

#### **KPI 5: Top 20 Assuntos por Pontuação de Engajamento (Melhorado)**

Em vez de apenas a taxa de resposta, ordenamos pelo `engagement_score` médio, que valoriza respostas rápidas.

> **Visualização:** Tabela.

```sql
-- Assuntos que geram as respostas mais valiosas (rápidas)
SELECT
  e.subject                                                             AS "Assunto",
  COUNT(*)                                                              AS "Enviados",
  SUM(e.is_replied::int)                                                AS "Respostas",
  ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(COUNT(*), 0), 2)         AS "Taxa de Resposta (%)",
  ROUND(AVG(e.engagement_score), 2)                                     AS "Pontuação Média"
FROM
  public.emails e
WHERE
  e.sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
  AND e.is_bounced IS FALSE
GROUP BY
  e.subject
HAVING
  COUNT(*) >= 20 -- Apenas assuntos com um volume mínimo para relevância estatística
ORDER BY
  "Pontuação Média" DESC, "Taxa de Resposta (%)" DESC
LIMIT 20;
```

-----

#### **KPI 6: Distribuição da Latência de Resposta (Novo)**

Entenda *quando* os clientes respondem. Isso ajuda a alinhar as expectativas e a otimizar o timing de follow-ups.

> **Visualização:** Gráfico de Pizza ou Barras.

```sql
-- Em quanto tempo as respostas chegam?
SELECT
  CASE
    WHEN reply_latency_sec < 3600             THEN '01. Em menos de 1 hora'
    WHEN reply_latency_sec < 14400            THEN '02. Entre 1 e 4 horas'
    WHEN reply_latency_sec < 43200            THEN '03. Entre 4 e 12 horas'
    WHEN reply_latency_sec < 86400            THEN '04. Entre 12 e 24 horas'
    WHEN reply_latency_sec < 172800           THEN '05. Entre 24 e 48 horas'
    ELSE                                           '06. Mais de 48 horas'
  END AS "Faixa de Latência",
  COUNT(*) AS "Total de Respostas"
FROM
  public.emails
WHERE
  is_replied = true AND sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY
  "Faixa de Latência"
ORDER BY
  "Faixa de Latência";
```

-----

#### **Seção 3: Saúde da Operação e Diagnósticos**

-----

#### **KPI 7: Ranking de Performance por Conta (Novo)**

Uma visão clara de quais contas estão performando melhor com base em um índice que combina taxa de resposta e pontuação.

> **Visualização:** Tabela.

```sql
-- Ranking de contas por um índice de performance (taxa de resposta * pontuação média)
SELECT
  a.email_address                                                                   AS "Conta",
  ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0), 2) AS "Taxa de Resposta (%)",
  ROUND(AVG(e.engagement_score), 2)                                                 AS "Pontuação Média",
  -- Índice de Performance: um score mais alto indica melhor performance geral
  ROUND((SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0)) * AVG(e.engagement_score), 2) AS "Índice de Performance"
FROM
  public.emails e
JOIN
  public.accounts a ON a.id = e.account_id
WHERE
  e.sent_datetime >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  a.email_address
ORDER BY
  "Índice de Performance" DESC;
```

-----

#### **KPI 8: Mapa de Calor de Engajamento por Hora do Dia (Melhorado)**

Em vez de apenas volume, este mapa mostra as horas do dia com **maior pontuação de engajamento**, revelando os melhores horários para enviar e-mails.

> **Visualização:** Mapa de Calor (Heatmap).

```sql
-- Média de engagement_score por hora do dia e dia da semana
SELECT
  -- Extrai a hora do dia (0-23)
  EXTRACT(hour FROM sent_datetime AT TIME ZONE 'America/Sao_Paulo') AS "Hora do Dia",
  -- Extrai o dia da semana (0=Domingo, 1=Segunda, etc.) e formata para ordenação
  TO_CHAR(sent_datetime AT TIME ZONE 'America/Sao_Paulo', 'ID - Day') AS "Dia da Semana",
  ROUND(AVG(engagement_score)) AS "Pontuação Média de Engajamento"
FROM
  public.emails
WHERE
  sent_datetime >= CURRENT_DATE - INTERVAL '28 days'
GROUP BY
  1, 2
ORDER BY
  2, 1;
```

-----

#### **KPI 9: Diagnóstico de Bounces por Domínio (Novo)**

Identifica se há problemas de entrega com domínios específicos, ajudando a detectar bloqueios ou problemas de reputação.

> **Visualização:** Tabela.

```sql
-- Domínios com maior número de bounces
SELECT
  -- Extrai o domínio do endereço de e-mail
  SUBSTRING(recipient FROM '@(.*)$') AS "Domínio do Destinatário",
  COUNT(*) AS "Total de Bounces"
FROM (
  SELECT unnest(recipient_addresses) AS recipient
  FROM public.emails
  WHERE is_bounced = TRUE AND sent_datetime >= CURRENT_DATE - INTERVAL '90 days'
) AS unnested_emails
GROUP BY
  1
HAVING
  COUNT(*) > 5 -- Mostra apenas domínios com um número significativo de falhas
ORDER BY
  "Total de Bounces" DESC
LIMIT 25;
```

-----

#### **KPI 10: Comparativo de Temperatura por Conta (Otimizado)**

Visão percentual da distribuição de temperatura, permitindo uma comparação justa entre contas com volumes de envio diferentes.

> **Visualização:** Gráfico de Barras Empilhadas (100%).

```sql
-- Distribuição percentual de temperatura por conta
SELECT
  a.email_address                                                                    AS "Conta",
  ROUND(100.0 * SUM((e.temperature_label = 'quente')::int) / COUNT(*), 1)             AS "% Quente",
  ROUND(100.0 * SUM((e.temperature_label = 'morno')::int) / COUNT(*), 1)              AS "% Morno",
  ROUND(100.0 * SUM((e.temperature_label = 'frio')::int) / COUNT(*), 1)               AS "% Frio",
  COUNT(*)                                                                           AS "Total de E-mails"
FROM
  public.emails e
JOIN
  public.accounts a ON a.id = e.account_id
WHERE
  e.sent_datetime >= DATE_TRUNC('month', CURRENT_DATE) -- Filtro para o mês atual
GROUP BY
  a.email_address
ORDER BY
  "% Quente" DESC;
```

-----

#### **KPI 11 & 12: Listas de Diagnóstico (Originais Otimizadas)**

Consultas diretas para encontrar os principais ofensores de bounce e os destinatários mais engajados.

> **Visualização:** Tabela.

```sql
-- KPI 11: Top 30 Destinatários com mais Bounces
SELECT
  unnest(e.recipient_addresses) AS "Destinatário",
  COUNT(*)                      AS "Total de Bounces"
FROM public.emails e
WHERE e.is_bounced IS TRUE
GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

-- KPI 12: Top 30 Destinatários mais Engajados (por pontuação)
SELECT
  unnest(e.recipient_addresses) AS "Destinatário",
  SUM(e.engagement_score)       AS "Pontuação Total",
  COUNT(*)                      AS "E-mails Recebidos"
FROM public.emails e
WHERE e.is_replied = TRUE
GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
```