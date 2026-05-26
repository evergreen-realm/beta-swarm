# Research Summary: antigravity-awesome-skills
**Repo:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)

## Key Patterns
- **Skill Bundling**: Packaging agent instructions, scripts, and resources into self-contained folders.
- **Global Registry**: A centralized list of community-curated skills.
- **One-command Installation**: Simplifying the addition of new capabilities to agents.

## What to Steal
- The **Installation CLI** pattern: Automating the cloning and dependency setup of remote skills.
- **Version Tracking**: Ensuring skills are compatible with the current swarm version.

## Integration Plan
- Implement `install_from_github(url)` in `skills_browser.py`.
- Add a "Marketplace" tab to the dashboard (UI update) that lists skills from the awesome-skills repo.
