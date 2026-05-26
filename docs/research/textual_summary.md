# Research Summary: textual
**Repo:** [Textualize/textual](https://github.com/Textualize/textual)

## Key Patterns
- **Reactive Programming**: UI elements update automatically when data changes via `reactive` properties.
- **CSS-based Styling**: Separation of layout and style using a CSS dialect.
- **Widget Composition**: Building complex interfaces from simple, reusable components.

## What to Steal
- **Message Passing**: Using `post_message` for thread-safe UI updates.
- **Sparklines**: For compact, real-time data visualization.

## Integration Plan
- Implement a `SwarmMetricCard` widget that combines a title, value, and sparkline.
- Add a `PipelineProgressBar` that changes color based on the current stage status.
