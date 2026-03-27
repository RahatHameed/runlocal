# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `workflow-status` now displays error details when a workflow fails, including failed test names, error messages, and relevant context

### Fixed
- `workflow-status` now filters by branch configured in `projects.yaml` instead of showing the latest run across all branches
