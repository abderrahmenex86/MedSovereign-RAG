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
| `src/components/ChatInterface.jsx` | Transcript, input, streaming lifecycle |
| `src/components/AgentUI.jsx` | History panel and reasoning/sources panel |
| `src/components/Markdown.jsx` | Markdown renderer with explicit element styles |
| `src/lib/api.js` | Buffered NDJSON client |
| `src/store.js` | Zustand sessions; only durable state is persisted |
| `src/index.css` | Tailwind v4 theme tokens and base styles |

Sessions and panel preferences are persisted in `localStorage`. Transient state
(`isGenerating`, the in-flight draft) is deliberately excluded so a reload
cannot leave the UI stuck.
