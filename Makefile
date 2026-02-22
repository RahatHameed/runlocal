.PHONY: help up down list file-reader workflow-trigger workflow-status workflow-list workflow-status-all setup clean

.DEFAULT_GOAL := help

# Colors
YELLOW := \033[33m
GREEN := \033[32m
CYAN := \033[36m
RED := \033[31m
RESET := \033[0m

# Check for .env file
ENV_EXISTS := $(shell test -f .env && echo yes)

help: ## Show this help
	@echo ""
	@echo "$(CYAN)runlocal$(RESET)"
	@echo "$(YELLOW)===================$(RESET)"
	@echo ""
	@echo "$(GREEN)Setup:$(RESET)"
	@echo "  make up               - Setup and build (run this first)"
	@echo "  make setup            - Interactive setup for .env file"
	@echo "  make down             - Stop and remove containers"
	@echo ""
	@echo "$(GREEN)Scripts:$(RESET)"
	@echo "  make list             - List available scripts"
	@echo "  make file-reader      - Read files (pattern=*.py verbose=1)"
	@echo "  make workflow-trigger - Trigger workflow (project=name wait=1)"
	@echo "  make workflow-status  - Check workflow status (project=name)"
	@echo "  make workflow-list    - List workflows and inputs (project=name)"
	@echo "  make workflow-status-all - Check status of all projects"
	@echo ""
	@echo "$(GREEN)Examples:$(RESET)"
	@echo "  make file-reader pattern=\"*.txt\""
	@echo "  make workflow-trigger project=test"
	@echo "  make workflow-trigger project=test wait=1"
	@echo "  make workflow-status project=test"
	@echo "  make workflow-list project=test"
	@echo "  make workflow-status-all"
	@echo ""

# =============================================================================
# Setup
# =============================================================================

# Pre-flight check for .env
check-env:
ifndef ENV_EXISTS
	@echo ""
	@echo "$(RED)Error: .env file not found$(RESET)"
	@echo ""
	@echo "$(YELLOW)Setup required:$(RESET)"
	@echo "  1. Run: $(GREEN)make setup$(RESET)"
	@echo "  2. Or manually: $(GREEN)cp .env.example .env && nano .env$(RESET)"
	@echo ""
	@echo "$(YELLOW)Get a GitHub token at:$(RESET)"
	@echo "  https://github.com/settings/tokens"
	@echo "  Required scopes: repo, workflow"
	@echo ""
	@exit 1
endif
	@if [ -z "$${GITHUB_TOKEN}" ] && ! grep -q "GITHUB_TOKEN=." .env 2>/dev/null; then \
		echo ""; \
		echo "$(RED)Error: GITHUB_TOKEN not set in .env$(RESET)"; \
		echo ""; \
		echo "$(YELLOW)Add your token to .env:$(RESET)"; \
		echo "  GITHUB_TOKEN=ghp_xxxxx"; \
		echo ""; \
		exit 1; \
	fi

setup: ## Interactive setup for .env file
	@echo ""
	@echo "$(CYAN)Setting up runlocal...$(RESET)"
	@echo ""
	@if [ ! -f .env ]; then \
		echo "GITHUB_TOKEN=" > .env; \
		echo "$(GREEN)Created .env file$(RESET)"; \
	fi
	@echo "$(YELLOW)Enter your GitHub token (or press Enter to skip):$(RESET)"
	@echo "Get one at: https://github.com/settings/tokens (scopes: repo, workflow)"
	@read -p "> " token; \
	if [ -n "$$token" ]; then \
		sed -i "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$$token/" .env; \
		echo "$(GREEN)Token saved to .env$(RESET)"; \
	else \
		echo "$(YELLOW)Skipped. Edit .env manually to add your token.$(RESET)"; \
	fi
	@echo ""
	@test -f projects.yaml || cp projects.yaml.example projects.yaml 2>/dev/null || true
	@test -f config.yaml || cp config.yaml.example config.yaml 2>/dev/null || true
	@echo "$(GREEN)Setup complete! Run 'make up' to build.$(RESET)"

up: ## Setup config files and build Docker image
	@test -f .env || cp .env.example .env 2>/dev/null || echo "GITHUB_TOKEN=" > .env
	@test -f projects.yaml || cp projects.yaml.example projects.yaml 2>/dev/null || true
	@test -f config.yaml || cp config.yaml.example config.yaml 2>/dev/null || true
	@docker compose build
	@echo ""
	@if grep -q "GITHUB_TOKEN=$$" .env 2>/dev/null || grep -q "GITHUB_TOKEN=ghp_xxxxx" .env 2>/dev/null; then \
		echo "$(YELLOW)Note: Edit .env with your GITHUB_TOKEN$(RESET)"; \
		echo "  Run: $(GREEN)make setup$(RESET) for interactive setup"; \
	else \
		echo "$(GREEN)Ready!$(RESET)"; \
	fi

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

workflow-trigger: check-env ## Trigger workflow (project=name wait=1 verbose=1 param=key=value)
	@if [ -z "$(project)" ]; then \
		echo "$(YELLOW)Error: project is required$(RESET)"; \
		echo "Usage: make workflow-trigger project=test"; \
		exit 1; \
	fi
	@docker compose run --rm runlocal workflow-dispatch --project $(project) $(WAIT_FLAG) $(VERBOSE_FLAG) $(PARAM_FLAG)

workflow-status: check-env ## Check workflow status (project=name workflow=trigger.yaml)
	@if [ -z "$(project)" ]; then \
		echo "$(YELLOW)Error: project is required$(RESET)"; \
		echo "Usage: make workflow-status project=test"; \
		exit 1; \
	fi
	@docker compose run --rm runlocal workflow-status --project $(project) $(WORKFLOW_FLAG) $(VERBOSE_FLAG)

workflow-list: check-env ## List workflows and inputs (project=name verbose=1)
	@if [ -z "$(project)" ]; then \
		echo "$(YELLOW)Error: project is required$(RESET)"; \
		echo "Usage: make workflow-list project=test"; \
		exit 1; \
	fi
	@docker compose run --rm runlocal workflow-list --project $(project) $(VERBOSE_FLAG)

workflow-status-all: check-env ## Check status of all configured projects
	@docker compose run --rm runlocal workflow-status-all $(VERBOSE_FLAG)

# =============================================================================
# Maintenance
# =============================================================================

clean: ## Remove Docker images and volumes
	@docker compose down --rmi local --volumes --remove-orphans
