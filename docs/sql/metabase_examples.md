# Exemplos de consultas SQL para Metabase

<p align="right">
  <a href="../../README.md">⬅️ Voltar para o README</a>
</p>

## 1 – Resumo diário por conta
Visão geral: envios, entregas, respostas e taxas *clean*.

```sql
SELECT
  a.email_address                        AS "Conta",
  m.date                                 AS "Data",
  m.total_sent                           AS "Enviados (clean)",
  m.total_delivered                      AS "Entregues",
  m.total_bounced                        AS "Bounces",
  m.total_replied                        AS "Respondidos",
  ROUND(m.delivery_rate / 100.0, 2)      AS "Delivery Rate (%)",
  ROUND(m.reply_rate    / 100.0, 2)      AS "Reply Rate (%)",
  m.temperature_label                    AS "Temperatura da campanha"
FROM   public.metrics  m
JOIN   public.accounts a ON m.account_id = a.id
ORDER  BY m.date DESC, a.email_address;
```

---

## 2 – Evolução das taxas (últimos 30 dias)

> Ideal para **linha temporal** com duas séries: `Delivery Rate` e `Reply Rate`.

```sql
SELECT
  m.date,
  AVG(ROUND(m.delivery_rate / 100.0, 2)) AS "Delivery Rate (%)",
  AVG(ROUND(m.reply_rate    / 100.0, 2)) AS "Reply Rate (%)"
FROM public.metrics m
WHERE m.date >= CURRENT_DATE - INTERVAL '30 day'
GROUP BY m.date
ORDER BY m.date;
```

---

## 3 – Distribuição de temperatura (último lote)

> **Gráfico de rosca** exibindo % de e-mails quentes / mornos / frios.

```sql
SELECT
  e.temperature_label            AS "Temperatura",
  COUNT(*)                       AS "E-mails"
FROM public.emails e
JOIN public.metrics m ON m.run_at = (
    SELECT MAX(run_at) FROM public.metrics
) AND m.account_id = e.account_id
GROUP BY e.temperature_label;
```

---

## 4 – Top 20 assuntos com maior reply rate

> Para detectar “assuntos campeões”.

```sql
SELECT
  LEFT(e.subject, 120)                         AS "Assunto",
  COUNT(*)                                     AS "Enviados",
  SUM(e.is_replied::int)                       AS "Respondidos",
  ROUND(100.0 * SUM(e.is_replied::int) / COUNT(*), 2) AS "Reply Rate (%)"
FROM public.emails e
WHERE e.sent_datetime >= CURRENT_DATE - INTERVAL '90 day'
  AND e.is_bounced IS FALSE
GROUP BY e.subject
HAVING COUNT(*) >= 30                          -- mínimo de envios
ORDER BY "Reply Rate (%)" DESC
LIMIT 20;
```

---

## 5 – Destinatários que mais devolvem “bounce”

> Ajuda a limpar listas ou corrigir domínios.

```sql
SELECT
  unnest(e.recipient_addresses)                AS "Destinatário",
  COUNT(*)                                     AS "Bounces"
FROM public.emails e
WHERE e.is_bounced IS TRUE
GROUP BY 1
ORDER BY "Bounces" DESC
LIMIT 30;
```

---

## 6 – Mapa calor (dia × hora) de envios

> Use visualização “heatmap”.

```sql
SELECT
  DATE_TRUNC('hour', e.sent_datetime)  AS "Hora",
  COUNT(*)                             AS "Envios"
FROM public.emails e
WHERE e.sent_datetime >= CURRENT_DATE - INTERVAL '14 day'
GROUP BY 1
ORDER BY 1;
```

---

## 7 – Taxa de resposta por conta (últimos 7 dias)

```sql
SELECT
  a.email_address                       AS "Conta",
  ROUND(100.0 * SUM(e.is_replied::int) /
        NULLIF(SUM((NOT e.is_bounced)::int),0), 2) AS "Reply Rate (%)",
  COUNT(*)                              AS "Enviados"
FROM public.emails   e
JOIN public.accounts a ON a.id = e.account_id
WHERE e.sent_datetime >= CURRENT_DATE - INTERVAL '7 day'
GROUP BY a.email_address
ORDER BY "Reply Rate (%)" DESC;
```

---

## 8 – Comparativo “quentes” vs “mornos” vs “frios” por conta

```sql
SELECT
  a.email_address                               AS "Conta",
  SUM((e.temperature_label = 'quente')::int)    AS "Quentes",
  SUM((e.temperature_label = 'morno')::int)     AS "Mornos",
  SUM((e.temperature_label = 'frio')::int)      AS "Frios"
FROM public.emails e
JOIN public.accounts a ON a.id = e.account_id
GROUP BY a.email_address
ORDER BY "Quentes" DESC;
```

