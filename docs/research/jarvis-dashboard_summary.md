# Research Summary: jarvis-dashboard
**Repo:** [AndrewKochulab/jarvis-dashboard](https://github.com/AndrewKochulab/jarvis-dashboard)

## Key Patterns
- **Modular Widget System**: Every UI element is a self-contained widget with its own data polling logic.
- **Voice-First Design**: Primary interaction is voice-based, with visual feedback as secondary.
- **Agent Fleet Visualization**: High-density grid view showing statuses of dozens of agents simultaneously.

## What to Steal
- The **JSON-based widget configuration** allowing users to enable/disable dashboard panels without changing code.
- **Cross-platform process management** patterns for running STT/TTS in the background.

## Integration Plan
- Implement `dashboard/widgets.json` to control which cards appear in the web HUD and TUI.
- Add a widget registry to `collector.py` that filters data based on this config.
