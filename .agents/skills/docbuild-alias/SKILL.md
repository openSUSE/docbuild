# Skill - Running the docbuild tool via Custom Aliases

## Context

This repository provides custom shell aliases to make running tasks easier without needing to type long `uv run` commands constantly. 

## Procedure

1. Before attempting to run custom repository commands, you must source the alias script.
2. Run: `source devel/activate-aliases.sh`
3. Once sourced, you can use the custom aliases available in the environment (for example, `docbuild`, `upytest`, `makedocs`).
4. **CRITICAL**: To run the main CLI tool, you must *always* use the dedicated agent environment configuration to avoid conflicting with or polluting the human developer's local host state.
5. Always run commands using the `--env-config` flag pointing to the agent config: `docbuild --env-config env.agent.toml <command>`. Do not run `docbuild` without this isolated environment configuration.

## Checklist

- [ ] Did you run `source devel/activate-aliases.sh` in the current terminal session?
- [ ] Are you using the alias directly instead of invoking python/uv manually?

## Validation

Run `alias` or `type docbuild` in the terminal to verify the alias is active before attempting to build or test.
