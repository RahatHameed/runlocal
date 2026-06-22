# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-22

### Added
- Initial release of the script runner.
- `workflow-dispatch` command to trigger GitHub Actions workflows and monitor them to completion.
- `workflow-status` command to check the status of the last workflow run, including failed jobs and error details (failed test names, error messages, and relevant context) when a run fails.
- `workflow-status-all` command to check status across all configured projects.
- `workflow-list` command to list available workflows.
- `file-reader` command.
- Project configuration via `projects.yaml` and runner settings via `config.yaml`.

### Fixed
- `workflow-status` now filters by the branch configured in `projects.yaml` instead of showing the latest run across all branches.
