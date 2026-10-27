# dev19 — UI viewport stability and Swedish headings

Version: `1.1.0-dev.19`
Baseline: `1.1.0-dev.18` / source identity `b2dac2ad55a38d8fd3c277c5eda8d2dcc92c696329f6cd67df52d621c4b6800f`

Scope is UI-only maintenance. No Engine, protocol, topology-model, dependency, or Phase E behavior is changed.

## Layout contract

- The application frame is bounded to the browser viewport.
- The workspace grid consumes only the remaining viewport height.
- The topology panel owns the entire left workspace column and has a stable height independent of right-panel content.
- The right control/results column owns vertical scrolling.
- Runtime results and packaged media are inside the right scroll column, not below the topology.
- Collapsing or expanding every right-side `<details>` panel cannot change topology canvas height.

## Localization contract

High-level visible section/panel headings are Swedish (for example Uppdrag, Test, Fynd, Evidens, Framsteg, Ledtrådar, Lärande/mål, Felinjektion and Guidad felsökning). Internal identifiers, data attributes, Engine truth/status values and model semantics remain unchanged.
