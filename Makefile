.PHONY: help up down list file-reader workflow-trigger workflow-status clean

.DEFAULT_GOAL := help

# Colors
YELLOW := \033[33m
GREEN := \033[32m
CYAN := \033[36m
RESET := \033[0m

help: ## Show this help
	@echo ""
	@echo "$(CYAN)runlocal$(RESET)"
	@echo "$(YELLOW)===================$(RESET)"
	@echo ""
	@echo "$(GREEN)Setup:$(RESET)"
	@echo "  make up               - Setup and build (run this first)"
	@echo "  make down             - Stop and remove containers"
	@echo ""
	@echo "$(GREEN)Scripts:$(RESET)"
	@echo "  make list             - List available scripts"
	@echo "  make file-reader      - Read files (pattern=*.py verbose=1)"
	@echo "  make workflow-trigger - Trigger workflow (project=name wait=1)"
	@echo "  make workflow-status  - Check workflow status (project=name)"
	@echo ""
	@echo "$(GREEN)Examples:$(RESET)"
	@echo "  make file-reader pattern=\"*.txt\""
	@echo "  make workflow-trigger project=test"
	@echo "  make workflow-trigger project=test wait=1"
	@echo "  make workflow-status project=test"
	@echo ""

# =============================================================================
# Setup
# =============================================================================

up: ## Setup config files and build Docker image
	@test -f .env || cp .env.example .env
	@test -f projects.yaml || cp projects.yaml.example projects.yaml
	@test -f config.yaml || cp config.yaml.example config.yaml 2>/dev/null || true
	@docker compose build
	@echo ""
	@echo "$(GREEN)Ready! Edit .env with your GITHUB_TOKEN$(RESET)"

down: ## Stop and remove containers
	@docker compose down --remove-orphans

# =============================================================================
# Scripts
# =============================================================================

pattern ?= *
project ?=
workflow ?=
verbose ?=
wait ?=
param ?=

ifeq ($(verbose),1)
	VERBOSE_FLAG := --verbose
else
	VERBOSE_FLAG :=
endif

ifeq ($(wait),1)
	WAIT_FLAG :=
else
	WAIT_FLAG := --no-wait
endif

ifneq ($(param),)
	PARAM_FLAG := --param $(param)
else
	PARAM_FLAG :=
endif

ifneq ($(workflow),)
	WORKFLOW_FLAG := --workflow $(workflow)
else
	WORKFLOW_FLAG :=
endif

list: ## List available scripts
	@docker compose run --rm runlocal --list

file-reader: ## Read files (pattern=*.py verbose=1)
	@docker compose run --rm runlocal file-reader --pattern "$(pattern)" $(VERBOSE_FLAG)

workflow-trigger: ## Trigger workflow (project=name wait=1 verbose=1 param=key=value)
	@if [ -z "$(project)" ]; then \
		echo "$(YELLOW)Error: project is required$(RESET)"; \
		echo "Usage: make workflow-trigger project=test"; \
		exit 1; \
	fi
	@docker compose run --rm runlocal workflow-dispatch --project $(project) $(WAIT_FLAG) $(VERBOSE_FLAG) $(PARAM_FLAG)

workflow-status: ## Check workflow status (project=name workflow=trigger.yaml)
	@if [ -z "$(project)" ]; then \
		echo "$(YELLOW)Error: project is required$(RESET)"; \
		echo "Usage: make workflow-status project=test"; \
		exit 1; \
	fi
	@docker compose run --rm runlocal workflow-status --project $(project) $(WORKFLOW_FLAG) $(VERBOSE_FLAG)

# =============================================================================
# Maintenance
# =============================================================================

clean: ## Remove Docker images and volumes
	@docker compose down --rmi local --volumes --remove-orphans
