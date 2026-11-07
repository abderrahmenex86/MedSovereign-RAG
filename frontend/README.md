# Frontend

React 19 + Vite client for MedSovereign-RAG. It streams NDJSON events from the
FastAPI backend and shows the answer, the retrieved sources, and the agent's
reasoning trace side by side.

## Run

```bash
npm install
npm run dev
```

The client defaults to `http://localhost:8000`. To point it elsewhere:

```bash
cp .env.example .env
# edit VITE_API_URL
```

For UI work without the backend, use demo mode:

```bash
VITE_DEMO_MODE=true npm run dev
# or open http://localhost:5173/?demo=1
```

Demo mode simulates streaming tokens, sources, and the reasoning trace entirely
in the browser. The interface shows a **Demo** badge and “Demo mode · sample
evidence” in the sidebar so it is never confused with a live run.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run lint` | ESLint (no errors allowed) |
| `npm run preview` | Serve the production build |

## Layout

| Path | Purpose |
| --- | --- |
| `src/components/ChatInterface.jsx` | Transcript, composer, streaming lifecycle, health status |
| `src/components/AgentUI.jsx` | Consultation sidebar and the Sources / Reasoning evidence panel |
| `src/components/Markdown.jsx` | Markdown renderer with explicit element styles |
| `src/components/ui.jsx` | Small shadcn-style primitives: button, badge, tabs, spinner |
| `src/lib/api.js` | Buffered NDJSON client and health check |
| `src/store.js` | Zustand sessions; only durable state is persisted |
| `src/index.css` | Tailwind v4 theme tokens, fonts, and base styles |

## Design

The interface is a white, navy-accented clinical workspace. Poppins carries the
interface, body text, headlines, and wordmark. The typeface is SIL OFL 1.1 and is
loaded from Google Fonts.

Sessions and panel preferences are persisted in `localStorage`. Transient state
(`isGenerating`, the in-flight draft) is deliberately excluded so a reload
cannot leave the UI stuck.
