#!/bin/bash
set -e
METABASE_HOST="http://localhost:3878"
METABASE_USER="test@mail.com"
METABASE_PASSWORD="My@4Pass50"
DB_NAME="Email Metrics DB"
COLLECTION_NAME="Análise de Campanhas de E-mail"
DASHBOARD_NAME="Dashboard de Performance de E-mail"

echo "Iniciando provisionamento do dashboard..."

api_call() { curl -s -X "$1" -H "Content-Type: application/json" -H "X-Metabase-Session: $SESSION_TOKEN" -d "$3" "$METABASE_HOST/api$2"; }

echo "➡️ 1/8: Autenticando na API..."
SESSION_TOKEN=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"username\": \"$METABASE_USER\", \"password\": \"$METABASE_PASSWORD\"}" "$METABASE_HOST/api/session" | jq -r '.id')
if [[ "$SESSION_TOKEN" == "null" || -z "$SESSION_TOKEN" ]]; then echo "❌ Erro na autenticação." && exit 1; fi
echo "✅ Token de sessão obtido."

echo "➡️ 2/8: Limpando execuções anteriores..."
OLD_DASH_ID=$(api_call "GET" "/dashboard" | jq --arg name "$DASHBOARD_NAME" '.[] | select(.name == $name) | .id')
if [[ -n "$OLD_DASH_ID" ]]; then api_call "PUT" "/dashboard/$OLD_DASH_ID" '{"archived": true}' > /dev/null; echo " -> Dashboard antigo arquivado."; fi
OLD_COLLECTION_ID=$(api_call "GET" "/collection" | jq --arg name "$COLLECTION_NAME" '.[] | select(.name == $name) | .id')
if [[ -n "$OLD_COLLECTION_ID" ]]; then api_call "PUT" "/collection/$OLD_COLLECTION_ID" '{"archived": true}' > /dev/null; echo " -> Coleção antiga arquivada."; fi

echo "➡️ 3/8: Buscando ID do banco de dados..."
DB_ID=$(api_call "GET" "/database" | jq --arg name "$DB_NAME" '.data[] | select(.name == $name) | .id')
if [ -z "$DB_ID" ]; then echo "❌ Banco de dados '$DB_NAME' não encontrado." && exit 1; fi
echo "✅ Banco de dados encontrado com ID: $DB_ID"

echo "➡️ 4/8: Criando a coleção '$COLLECTION_NAME'..."
COLLECTION_PAYLOAD=$(jq -n --arg name "$COLLECTION_NAME" '{name: $name, color: "#509EE3"}')
COLLECTION_ID=$(api_call "POST" "/collection" "$COLLECTION_PAYLOAD" | jq '.id')
echo "✅ Coleção criada com ID: $COLLECTION_ID"

echo "➡️ 5/8: Criando as 25 perguntas..."
declare -A CARD_IDS CARD_NAMES CARD_VIZ
CARD_NAMES=([1]="KPI 1: Resumo Diário" [2]="KPI 2: Funil do Dia" [3]="KPI 3: Ranking de Performance Mensal" [4]="KPI 4: Comparativo de Temperatura Mensal" [5]="KPI 5: Evolução Anual (Taxa de Resposta)" [6]="KPI 6: Evolução Mensal (Taxa de Resposta)" [7]="KPI 7: Evolução Semanal (Taxas)" [8]="KPI 8: Evolução Semanal (Pontuação)" [9]="KPI 9: Evolução Semanal (Latência)" [10]="KPI 10: Análise de Pontuação" [11]="KPI 11: Distribuição de Latência" [12]="KPI 12: Engajamento por Dia da Semana" [13]="KPI 13: Engajamento por Hora do Dia" [14]="KPI 14: Top 20 Assuntos por Performance" [15]="KPI 15: Evolução da Taxa de Bounce" [16]="KPI 16: Top Domínios com Bounces" [17]="KPI 17: Top Destinatários com Bounces" [18]="KPI 18: Destinatários Apenas com Bounces" [19]="KPI 19: Taxa de Resposta Média (Mensal)" [20]="KPI 20: Dias Ativos por Conta" [21]="KPI 21: Top 30 Destinatários Engajados" [22]="KPI 22: Performance Anual por Conta" [23]="KPI 23: Performance Mensal por Conta" [24]="KPI 24: Distribuição de Temperatura Anual" [25]="KPI 25: Performance Dia de Semana vs. Fim de Semana")
CARD_VIZ=([1]=table [2]=table [3]=table [4]=bar [5]=line [6]=line [7]=line [8]=line [9]=line [10]=bar [11]=pie [12]=bar [13]=bar [14]=table [15]=line [16]=table [17]=table [18]=table [19]=line [20]=table [21]=table [22]=bar [23]=bar [24]=pie [25]=bar)

for i in {1..25}; do
    SQL_QUERY=$(tr -s '[:space:]' ' ' < "questions/kpi_$i.sql")
    CARD_PAYLOAD=$(jq -n --arg name "${CARD_NAMES[$i]}" --arg display "${CARD_VIZ[$i]}" --arg query "$SQL_QUERY" --argjson db_id "$DB_ID" --argjson collection_id "$COLLECTION_ID" \
      '{name: $name, display: $display, visualization_settings: {}, dataset_query: {type: "native", native: { query: $query }, database: $db_id}, collection_id: $collection_id}')
    RESPONSE=$(api_call "POST" "/card" "$CARD_PAYLOAD")
    CARD_ID=$(echo "$RESPONSE" | jq '.id')
    if [[ "$CARD_ID" == "null" || -z "$CARD_ID" ]]; then echo "❌ Falha ao criar o card para o KPI $i. Resposta: $RESPONSE" && exit 1; fi
    CARD_IDS[$i]=$CARD_ID
    echo "  -> Pergunta '${CARD_NAMES[$i]}' criada com ID: $CARD_ID"
done
echo "✅ Todas as perguntas foram criadas."

echo "➡️ 6/8: Criando o dashboard..."
DASH_PAYLOAD=$(jq -n --arg name "$DASHBOARD_NAME" --argjson id "$COLLECTION_ID" '{name: $name, description: "Visão 360° da operação de e-mail", collection_id: $id}')
DASH_ID=$(api_call "POST" "/dashboard" "$DASH_PAYLOAD" | jq '.id')
echo "✅ Dashboard criado com ID: $DASH_ID"

echo "➡️ 7/8: Adicionando e posicionando os 25 cards..."
LAYOUT=(
  "${CARD_IDS[2]},0,0,18,5"  "${CARD_IDS[1]},0,5,18,6"
  "${CARD_IDS[7]},0,11,9,6"  "${CARD_IDS[9]},9,11,9,6"
  "${CARD_IDS[6]},0,17,9,6"  "${CARD_IDS[8]},9,17,9,6"
  "${CARD_IDS[3]},0,23,9,6"  "${CARD_IDS[4]},9,23,9,6"
  "${CARD_IDS[14]},0,29,18,7}" "${CARD_IDS[12]},0,36,9,6}"
  "${CARD_IDS[13]},9,36,9,6}" "${CARD_IDS[15]},0,42,18,6}"
  "${CARD_IDS[16]},0,48,9,7}" "${CARD_IDS[17]},9,48,9,7}"
  "${CARD_IDS[21]},0,55,9,7}" "${CARD_IDS[18]},9,55,9,7}"
  "${CARD_IDS[19]},0,62,9,6}" "${CARD_IDS[20]},9,62,9,6}"
  "${CARD_IDS[22]},0,68,6,6}" "${CARD_IDS[23]},6,68,6,6}"
  "${CARD_IDS[25]},12,68,6,6}" "${CARD_IDS[24]},0,74,18,6}"
)
for item in "${LAYOUT[@]}"; do
    IFS=',' read -r card_id col row size_x size_y <<< "$item"
    ADD_CARD_PAYLOAD="{\"card_id\": $card_id, \"col\": $col, \"row\": $row, \"size_x\": $size_x, \"size_y\": $size_y}"
    api_call "POST" "/dashboard/$DASH_ID/cards" "$ADD_CARD_PAYLOAD" > /dev/null
done
echo "✅ Cards adicionados e posicionados."

echo "➡️ 8/8: Ajustando tipos de gráficos..."
for i in {1..25}; do
    api_call "PUT" "/card/${CARD_IDS[$i]}" "{\"visualization_settings\": {}, \"display\": \"${CARD_VIZ[$i]}\"}" > /dev/null
done
echo "✅ Tipos de visualização ajustados."

echo "🎉 Provisionamento concluído com sucesso! Acesse: $METABASE_HOST/dashboard/$DASH_ID"