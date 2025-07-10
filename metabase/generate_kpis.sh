#!/bin/bash
mkdir -p questions
echo "Gerando 25 arquivos KPI SQL na pasta 'questions'..."

# --- Seção 1: Snapshots de Performance ---
cat <<'EOF' > questions/kpi_1.sql
SELECT DISTINCT ON (a.email_address, m.date) a.email_address AS "Conta", m.date AS "Data", m.total_sent AS "Enviados", m.total_delivered AS "Entregues", m.total_replied AS "Respostas", m.total_bounced AS "Bounces", ROUND(m.reply_rate / 100.0, 2) AS "Taxa Resposta (%)", m.temperature_label AS "Temp. Campanha", TO_CHAR((m.avg_reply_latency_sec || ' second')::interval, 'HH24:MI:SS') AS "Latência Média" FROM public.metrics m JOIN public.accounts a ON m.account_id = a.id ORDER BY a.email_address, m.date, m.run_at DESC;
EOF
cat <<'EOF' > questions/kpi_2.sql
SELECT a.email_address AS "Conta", COUNT(e.id) AS "Enviados", SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END) AS "Entregues", SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END) AS "Respondidos", ROUND(100.0 * SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END) / NULLIF(COUNT(e.id), 0), 2) AS "Taxa Entrega (%)", ROUND(100.0 * SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END), 0), 2) AS "Taxa Resposta (%)" FROM public.emails e JOIN public.accounts a ON e.account_id = a.id WHERE e.sent_datetime >= DATE_TRUNC('day', NOW() AT TIME ZONE 'America/Sao_Paulo') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 3 DESC;
EOF
cat <<'EOF' > questions/kpi_3.sql
SELECT a.email_address AS "Conta", ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0), 2) AS "Taxa Resposta (%)", ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média", ROUND((SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0)) * AVG(e.engagement_score), 2) AS "Índice de Performance" FROM public.emails e JOIN public.accounts a ON a.id = e.account_id WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '30 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 4 DESC;
EOF
cat <<'EOF' > questions/kpi_4.sql
SELECT a.email_address AS "Conta", ROUND(100.0*SUM((e.temperature_label='quente')::int)/COUNT(*),1) AS "% Quente", ROUND(100.0*SUM((e.temperature_label='morno')::int)/COUNT(*),1) AS "% Morno", ROUND(100.0*SUM((e.temperature_label='frio')::int)/COUNT(*),1) AS "% Frio", COUNT(*) AS "Total Envios" FROM public.emails e JOIN public.accounts a ON a.id=e.account_id WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '30 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 2 DESC;
EOF

# --- Seção 2: Evolução Temporal (Anual, Mensal, Semanal) ---
cat <<'EOF' > questions/kpi_5.sql
SELECT DATE_TRUNC('year', e.sent_datetime)::date AS "Ano", a.email_address AS "Conta", COUNT(e.id) AS "Total Envios", ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0), 2) AS "Taxa de Resposta Anual (%)" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_6.sql
SELECT DATE_TRUNC('month', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Mês", a.email_address AS "Conta", COUNT(e.id) AS "Total Envios", ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(SUM((NOT e.is_bounced)::int), 0), 2) AS "Taxa de Resposta Mensal (%)" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.sent_datetime >= DATE_TRUNC('year', CURRENT_DATE) AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_7.sql
SELECT DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana", a.email_address AS "Conta", ROUND(100.0*SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END)/NULLIF(COUNT(e.id),0),2) AS "Taxa de Entrega (%)", ROUND(100.0*SUM(CASE WHEN e.is_replied THEN 1 ELSE 0 END)/NULLIF(SUM(CASE WHEN NOT e.is_bounced THEN 1 ELSE 0 END),0),2) AS "Taxa de Resposta (%)" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_8.sql
SELECT DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana", a.email_address AS "Conta", ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média de Engajamento" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_9.sql
SELECT DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana", a.email_address AS "Conta", AVG(e.reply_latency_sec)/3600 AS "Latência Média (Horas)", COUNT(e.id) AS "Nº Respostas" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.is_replied=true AND e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF

# --- Seção 3: Análise de Engajamento ---
cat <<'EOF' > questions/kpi_10.sql
SELECT a.email_address AS "Conta", e.engagement_score AS "Pontuação", COUNT(*) AS "Total de Respostas", TO_CHAR((AVG(e.reply_latency_sec) || ' second')::interval, 'DD"d "HH24:MI:SS') AS "Latência Média" FROM public.emails e JOIN public.accounts a ON e.account_id=a.id WHERE e.is_replied=true AND e.sent_datetime >= (CURRENT_DATE - INTERVAL '30 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2 DESC;
EOF
cat <<'EOF' > questions/kpi_11.sql
WITH latency_counts AS (SELECT CASE WHEN reply_latency_sec < 3600 THEN '01. Em menos de 1 hora' WHEN reply_latency_sec < 14400 THEN '02. Entre 1 e 4 horas' WHEN reply_latency_sec < 43200 THEN '03. Entre 4 e 12 horas' WHEN reply_latency_sec < 86400 THEN '04. Entre 12 e 24 horas' ELSE '05. Mais de 24 horas' END AS "Faixa de Latência", COUNT(*) AS "Total de Respostas" FROM public.emails WHERE is_replied = true AND sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') GROUP BY 1) SELECT "Faixa de Latência", "Total de Respostas", ROUND(100.0 * "Total de Respostas" / SUM("Total de Respostas") OVER(), 2) AS "Percentual (%)" FROM latency_counts ORDER BY 1;
EOF
cat <<'EOF' > questions/kpi_12.sql
SELECT TO_CHAR(sent_datetime AT TIME ZONE 'America/Sao_Paulo', 'ID - Day') AS "Dia da Semana", ROUND(AVG(engagement_score)) AS "Pontuação Média" FROM public.emails WHERE sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 1;
EOF
cat <<'EOF' > questions/kpi_13.sql
SELECT EXTRACT(hour FROM sent_datetime AT TIME ZONE 'America/Sao_Paulo') AS "Hora do Dia", ROUND(AVG(engagement_score)) AS "Pontuação Média" FROM public.emails WHERE sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 1;
EOF
cat <<'EOF' > questions/kpi_14.sql
SELECT e.subject AS "Assunto", COUNT(*) AS "Enviados", SUM(e.is_replied::int) AS "Respostas", ROUND(100.0 * SUM(e.is_replied::int) / NULLIF(COUNT(*), 0), 2) AS "Taxa Resposta (%)", ROUND(AVG(e.engagement_score), 2) AS "Pontuação Média" FROM public.emails e WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.is_bounced IS FALSE AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 HAVING COUNT(*) >= 20 ORDER BY 5 DESC, 4 DESC LIMIT 20;
EOF

# --- Seção 4: Saúde e Diagnósticos ---
cat <<'EOF' > questions/kpi_15.sql
SELECT DATE_TRUNC('week', e.sent_datetime AT TIME ZONE 'America/Sao_Paulo')::date AS "Semana", ROUND(100.0 * SUM(e.is_bounced::int) / COUNT(e.id), 2) AS "Taxa de Bounce (%)" FROM public.emails e WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 1;
EOF
cat <<'EOF' > questions/kpi_16.sql
SELECT SUBSTRING(recipient FROM '@(.*)$') AS "Domínio do Destinatário", COUNT(*) AS "Total de Bounces" FROM (SELECT unnest(recipient_addresses) AS recipient FROM public.emails WHERE is_bounced = TRUE AND sent_datetime >= (CURRENT_DATE - INTERVAL '90 days')) AS unnested_emails GROUP BY 1 HAVING COUNT(*) > 5 ORDER BY 2 DESC LIMIT 25;
EOF
cat <<'EOF' > questions/kpi_17.sql
SELECT unnest(e.recipient_addresses) AS "Destinatário", COUNT(*) AS "Total de Bounces", STRING_AGG(DISTINCT a.email_address, ', ') AS "Contas de Origem", MAX(e.sent_datetime)::date AS "Data do Último Bounce" FROM public.emails e JOIN public.accounts a ON e.account_id = a.id WHERE e.is_bounced IS TRUE AND e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
EOF
cat <<'EOF' > questions/kpi_18.sql
SELECT recipient AS "Destinatário Apenas com Bounce" FROM (SELECT unnest(recipient_addresses) AS recipient, COUNT(*) as total, SUM(CASE WHEN is_bounced THEN 1 ELSE 0 END) as bounces FROM public.emails GROUP BY 1) as subquery WHERE total = bounces AND total > 2 ORDER BY total DESC LIMIT 30;
EOF

# --- Seção 5: Análise de Contas e Destinatários ---
cat <<'EOF' > questions/kpi_19.sql
SELECT a.email_address as "Conta", DATE_TRUNC('month', m.date)::date as "Mês", ROUND(AVG(m.reply_rate)/100.0, 2) as "Taxa Média de Resposta (%)" FROM public.metrics m JOIN public.accounts a ON m.account_id=a.id GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_20.sql
SELECT a.email_address AS "Conta", MIN(e.sent_datetime)::date AS "Primeiro Envio", MAX(e.sent_datetime)::date AS "Último Envio", COUNT(DISTINCT e.sent_datetime::date) AS "Dias Ativos" FROM public.emails e JOIN public.accounts a ON a.id = e.account_id GROUP BY 1 ORDER BY 4 DESC;
EOF
cat <<'EOF' > questions/kpi_21.sql
SELECT unnest(e.recipient_addresses) AS "Destinatário", SUM(e.engagement_score) AS "Pontuação Total", ROUND(AVG(e.engagement_score), 1) AS "Pontuação Média", COUNT(*) AS "E-mails Respondidos" FROM public.emails e WHERE e.is_replied=TRUE AND e.sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') GROUP BY 1 ORDER BY 2 DESC, 3 DESC LIMIT 30;
EOF
cat <<'EOF' > questions/kpi_22.sql
SELECT a.email_address AS "Conta", AVG(e.engagement_score) AS "Pontuação Média no Ano" FROM emails e JOIN accounts a ON e.account_id=a.id WHERE e.sent_datetime >= DATE_TRUNC('year', CURRENT_DATE) AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 2 DESC;
EOF
cat <<'EOF' > questions/kpi_23.sql
SELECT a.email_address AS "Conta", AVG(e.engagement_score) AS "Pontuação Média no Mês" FROM emails e JOIN accounts a ON e.account_id=a.id WHERE e.sent_datetime >= (CURRENT_DATE - INTERVAL '30 days') AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1 ORDER BY 2 DESC;
EOF
cat <<'EOF' > questions/kpi_24.sql
SELECT a.email_address AS "Conta", temperature_label AS "Temperatura", COUNT(*) AS "Total" FROM emails e JOIN accounts a ON e.account_id=a.id WHERE e.sent_datetime >= DATE_TRUNC('year', CURRENT_DATE) AND e.subject NOT ILIKE 'ENC:%' AND e.subject NOT ILIKE 'FW:%' GROUP BY 1, 2 ORDER BY 1, 2;
EOF
cat <<'EOF' > questions/kpi_25.sql
SELECT EXTRACT(ISODOW FROM sent_datetime) AS day_of_week, CASE WHEN EXTRACT(ISODOW FROM sent_datetime) < 6 THEN 'Dia de Semana' ELSE 'Fim de Semana' END AS "Tipo de Dia", ROUND(AVG(engagement_score), 2) AS "Pontuação Média" FROM emails WHERE sent_datetime >= (CURRENT_DATE - INTERVAL '90 days') GROUP BY 1, 2 ORDER BY 1;
EOF

echo "Pronto! Os 25 arquivos KPI .sql foram gerados na pasta 'questions'."