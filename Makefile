# Makefile para o projeto Email-Metrics
# Simplifica tarefas comuns de desenvolvimento e operação.

# Define que os alvos não são arquivos, garantindo que sempre sejam executados.
.PHONY: help reset-run run-metrics provision-dashboard

# Comando padrão: exibe a ajuda. Executado quando 'make' é chamado sem argumentos.
help:
	@echo "----------------------------------------------------"
	@echo " Comandos disponíveis para o projeto Email-Metrics:"
	@echo "----------------------------------------------------"
	@echo "  make reset-run          - 💥 Destrói tudo (incluindo volumes), reconstrói e executa a coleta de métricas."
	@echo "  make run-metrics        - 🚀 Executa a coleta de métricas no ambiente existente."
	@echo "  make provision-dashboard  - 📊 Gera os arquivos SQL e provisiona o dashboard no Metabase."
	@echo "  make up                 - ⬆️  Inicia todos os serviços em segundo plano."
	@echo "  make down               - ⬇️  Para todos os serviços."
	@echo "  make logs               - 📜 Exibe os logs de todos os serviços."
	@echo ""

# Alvo para reconstruir todo o ambiente do zero e rodar a coleta.
# Útil para garantir um estado limpo.
reset-run:
	@echo "--- 💥 Destruindo todos os serviços e volumes..."
	docker compose down --volumes --remove-orphans
	@echo "--- ⬆️  Recriando e iniciando serviços em segundo plano..."
	docker compose up -d --build
	@echo "--- ⏳ Aguardando 40 segundos para o Metabase inicializar completamente..."
	sleep 40
	@echo "--- 🚀 Executando a coleta de métricas..."
	docker compose run --rm email-metrics python -m application.main --once
	@echo "--- ✅ Processo de reset e execução concluído."

# Alvo para executar apenas a coleta de métricas.
run-metrics:
	@echo "--- 🚀 Executando a coleta de métricas..."
	docker compose run --rm email-metrics python -m application.main --once
	@echo "--- ✅ Coleta de métricas concluída."

# Alvo para gerar os arquivos SQL e provisionar o dashboard no Metabase.
provision-dashboard:
	@echo "--- 📊 Configurando o dashboard do Metabase..."
	@echo "  -> Tornando scripts executáveis..."
	chmod +x metabase/generate_kpis.sh
	chmod +x metabase/provision_dashboard.sh
	@echo "  -> Gerando 25 arquivos de KPI SQL..."
	./metabase/generate_kpis.sh
	@echo "  -> Provisionando dashboard via API..."
	./metabase/provision_dashboard.sh
	@echo "--- ✅ Configuração do dashboard concluída."

# Alvos de conveniência para gerenciamento do Docker.
up:
	@echo "--- ⬆️  Iniciando todos os serviços em segundo plano..."
	docker compose up -d

down:
	@echo "--- ⬇️  Parando todos os serviços..."
	docker compose down

logs:
	@echo "--- 📜 Exibindo logs..."
	docker compose logs -f

