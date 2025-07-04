# Exemplos de consultas SQL para Metabase

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
