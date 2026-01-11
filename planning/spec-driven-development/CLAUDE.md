# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Kiro Spec-Driven Development Guide** - a documentation and tooling repository for systematic feature development using the three-phase spec process: **Requirements → Design → Tasks**.

This repository is primarily **documentation** (markdown files) with supporting tooling:
- No build required for the core documentation
- The MCP server and web app are optional components

## Repository Structure

```
.kiro/                  # Kiro AI assistant configuration
  steering/             # Project-specific guidelines (included in AI context)
  system/               # Kiro operational standards
skills/                 # Claude Code skills (agentskills.io format)
spec-process-guide/     # Main documentation content
  methodology/          # Core concepts and philosophy
  process/              # Three-phase workflow guides
  ai-reasoning/         # Decision frameworks
  prompting/            # AI communication strategies
  execution/            # Implementation guidance
  templates/            # Ready-to-use spec templates
  examples/             # Case studies and examples
  resources/            # Standards, tools, further reading
mcp-server/             # Python MCP server exposing Kiro prompts
kiro-web-app/           # React/Vite documentation viewer
commands/               # Standalone command documentation
```

## Commands

### Validate Skills
```bash
./scripts/validate-skills.sh
```
Checks all SKILL.md files in `skills/` for required YAML frontmatter fields and format compliance.

### MCP Server (Python)
```bash
cd mcp-server
pip install -e ".[dev]"       # Install with dev dependencies
pytest                        # Run tests
uvx kiro-mcp-server           # Run server via uvx
```

### Web App (React/Vite)
```bash
cd kiro-web-app
npm install
npm run dev                   # Development server
npm run build                 # Production build
npm run lint                  # ESLint
npm run type-check            # TypeScript check
```

## Key Concepts

### Three-Phase Spec Process
1. **Requirements** - EARS format (Easy Approach to Requirements Syntax) for clear, testable criteria
2. **Design** - Technical architecture, components, data models, interfaces
3. **Tasks** - Sequenced implementation steps with clear objectives

### Steering Documents
Files in `.kiro/steering/` provide project-specific context. They use YAML frontmatter to control inclusion:
- `inclusion: always` (default) - Always included
- `inclusion: fileMatch` with `fileMatchPattern` - Included when matching files are in context
- `inclusion: manual` - Only when explicitly referenced with `#steering-name`

### Skills Format
Skills in `skills/*/SKILL.md` follow agentskills.io specification:
- YAML frontmatter with `name`, `description` (required)
- Main heading and instructions for the agent
- Name must be lowercase alphanumeric with hyphens, max 64 chars

## Claude Code Plugin

Install as a Claude Code plugin:
```bash
/plugin marketplace add https://github.com/jasonkneen/kiro
/plugin install kiro-spec-driven@kiro-marketplace
```

## Editing Guidelines

- All documentation is markdown - maintain consistent formatting
- Use relative links for cross-references within `spec-process-guide/`
- Skills must pass `./scripts/validate-skills.sh` validation
- Templates in `spec-process-guide/templates/` should remain generic and reusable
