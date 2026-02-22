# runlocal

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

A lightweight, Dockerized framework for running local automation scripts.

## Features

- GitHub Actions workflow triggering and monitoring
- **Parameter validation** with auto-correction for case mismatches
- **Auto-detect workflow file extensions** (.yml/.yaml)
- **Parallel status checks** for all configured projects
- File reading with glob patterns and syntax highlighting
- Rich colored terminal output
- Easy to extend with new scripts

## Prerequisites

- Docker and Docker Compose
- GitHub token (only for workflow-dispatch)

## Quick Start

```bash
make up                            # Setup and build
make setup                         # Interactive .env setup (or edit .env manually)
make workflow-trigger project=test # Run a workflow
make workflow-status-all           # Check all projects
```

## Commands

| Command | Description |
|---------|-------------|
| `make up` | Setup and build (run this first) |
| `make setup` | Interactive setup for .env file |
| `make down` | Stop containers |
| `make list` | List available scripts |
| `make file-reader` | Read files |
| `make workflow-trigger` | Trigger workflow |
| `make workflow-status` | Check workflow status |
| `make workflow-list` | List workflows and their inputs |
| `make workflow-status-all` | Check status of all projects |
| `make clean` | Remove Docker images |

### Examples

```bash
# File reader
make file-reader pattern="*.py"
make file-reader pattern="*.txt" verbose=1

# Workflow trigger
make workflow-trigger project=test
make workflow-trigger project=test wait=1
make workflow-trigger project=test param=limit="PHP8.5/MySQL8.0"

# Workflow status
make workflow-status project=test

# Check all projects at once
make workflow-status-all

# List available workflows and inputs
make workflow-list project=test
```

### Parameter Validation

The tool automatically validates workflow parameters and corrects case mismatches:

```
$ make workflow-trigger project=myproject param=limit="PHP8.5/mariadb11"
Warning: Correcting 'PHP8.5/mariadb11' to 'PHP8.5/MariaDb11'
```

### What's happening under the hood?

```bash
make workflow-trigger project=test
# Runs: docker compose run --rm runlocal workflow-dispatch --project test --no-wait
```

## Setup

1. Create a GitHub token at https://github.com/settings/tokens (scopes: `repo`, `workflow`)
2. Add to `.env`:
   ```
   GITHUB_TOKEN=ghp_xxxxx
   ```
3. Configure projects in `projects.yaml`:
   ```yaml
   projects:
     test:
       repo: RahatHameed/runlocal-test
       workflow: test.yaml
       branch: main
       defaults:
         message: "Hello from runlocal!"
   ```

## Configuration

Edit `config.yaml` to change settings:

```yaml
workflow:
  poll_interval: 30    # seconds between status checks
  timeout: 3600        # max wait time (0 = unlimited)
  show_progress: true
```

## Creating New Scripts

1. Create `scripts/my_script.py`:

```python
from scripts.base import BaseScript, ScriptConfig, ScriptResult

class MyScript(BaseScript):
    config = ScriptConfig(
        name="my-script",
        description="Does something useful",
        version="1.0.0"
    )

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        return ScriptResult(success=True, message="Done")
```

2. Register in `scripts/__init__.py`:

```python
from scripts.my_script import MyScript

SCRIPTS = {
    # ...existing scripts...
    "my-script": MyScript,
}
```

3. Rebuild: `make clean && make up`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Script not found | Run `make clean && make up` |
| Unknown project | Check `projects.yaml` exists |
| Auth failed | Verify `GITHUB_TOKEN` in `.env` has correct scopes |

## License

MIT
