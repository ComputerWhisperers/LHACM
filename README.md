# LHACM

[![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)](https://github.com/computerwhisperers/LHACM/releases/tag/v1.0.1)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-custom%20integration-41BDF5.svg)](https://www.home-assistant.io/)
[![Providers](https://img.shields.io/badge/providers-GitLab%20%7C%20Gitea-FCA121.svg)](#configuration)
[![License](https://img.shields.io/badge/license-TBD-lightgrey.svg)](#lhacm)

Local Home Assistant Component Manager (LHACM) is a Home Assistant custom integration for managing custom components from self-hosted or remote GitLab and Gitea repositories.

LHACM is intended to follow the HACS user model while replacing the GitHub-only repository backend with GitLab and Gitea support.

## Current scope

Version `1.0.0` establishes the integration foundation:

- HACS-style Home Assistant config flow with no repository host URL in setup.
- Home Assistant sidebar panel with a HACS-style repository dashboard.
- Custom repositories dialog for adding GitLab and Gitea repository URLs by type.
- GitLab and Gitea provider clients.
- Repository metadata, tree, release, archive, and raw-file helpers.
- Services to add and install custom repositories from repository URLs.
- Install, update, uninstall, remove, and refresh lifecycle actions.
- Native Home Assistant update entities for installed repositories.
- Safe ZIP extraction into Home Assistant custom component paths.

Full HACS parity is the target. The next major areas are repository indexes from local GitLab/Gitea systems, background queues, repair flows, and richer validation.

## Installation

Copy `custom_components/lhacm` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

Add the integration from **Settings > Devices & services > Add integration > LHACM**.

Setup does not ask for GitLab or Gitea URLs. Repository locations are supplied when adding a custom repository, matching the HACS flow.

For private repositories, set an environment variable for the repository host:

`LHACM_TOKEN_GITLAB_EXAMPLE_COM`

## Services

`lhacm.add_repository`

Registers and validates a repository.

Example repository value:

`https://gitlab.example.com/group/custom-integration`

`lhacm.install_repository`

Downloads a repository archive and installs it into the target Home Assistant custom location.

## Repository layout

For Home Assistant integrations, LHACM expects one of these layouts:

- `custom_components/<domain>/manifest.json`
- `<domain>/manifest.json`
- `manifest.json` in repository root

The installed integration is copied to `custom_components/<domain>`.
