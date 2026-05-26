# Research Summary: openclaw-jarvis-ui
**Repo:** [jincocodev/openclaw-jarvis-ui](https://github.com/jincocodev/openclaw-jarvis-ui)

## Key Patterns
- **3D HUD Interaction**: Uses Three.js for immersive orb-based system feedback.
- **SSE (Server-Sent Events)**: Prefers SSE over WebSockets for one-way system monitoring to reduce overhead.
- **Memory Timeline**: Chronological view of agent decisions and task history.

## What to Steal
- The **SSE monitoring pattern** for lightweight performance tracking.
- **CSS Glow/Scanline** effects for the HUD background.

## Integration Plan
- Add a `/api/metrics/sse` endpoint to the FastAPI server.
- Update the web frontend to use SSE for system vitals (CPU/RAM) while keeping WebSockets for bi-directional mission control.
