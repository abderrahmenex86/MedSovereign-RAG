import { DEMO_HEALTH, demoStreamQuery, isDemoMode } from './demo';

const DEFAULT_API_URL = 'http://localhost:8000';
const env = import.meta.env || {};

export const API_URL = (env.VITE_API_URL || DEFAULT_API_URL).replace(
    /\/+$/,
    ''
);

export const DEMO_MODE = isDemoMode();

const errorDetail = async (response) => {
    try {
        const body = await response.json();
        if (typeof body?.detail === 'string') return body.detail;
        if (body?.detail) return JSON.stringify(body.detail);
    } catch {
        // Fall through to the status text.
    }
    return `Request failed with status ${response.status}`;
};

export async function fetchHealth({ signal } = {}) {
    if (DEMO_MODE) return DEMO_HEALTH;

    const response = await fetch(`${API_URL}/health`, { signal });

    if (!response.ok) {
        throw new Error(`Health check failed (${response.status})`);
    }

    return response.json();
}

export async function cancelRequest(requestId) {
    if (DEMO_MODE || !requestId) return;

    try {
        await fetch(`${API_URL}/api/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId }),
            keepalive: true,
        });
    } catch {
        // The request may already have finished; cancellation is best effort.
    }
}

/**
 * Stream NDJSON events from the backend.
 *
 * The network does not preserve write boundaries, so a JSON object can arrive
 * split across two reads. Everything is buffered until a newline proves the
 * line is complete; parsing per-chunk loses answers at random.
 */
export async function* streamQuery(payload, { signal } = {}) {
    if (DEMO_MODE) {
        yield* demoStreamQuery(payload, { signal });
        return;
    }

    const response = await fetch(`${API_URL}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal,
    });

    if (!response.ok) {
        throw new Error(await errorDetail(response));
    }

    if (!response.body) {
        throw new Error('Streaming is not supported in this browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            let newlineIndex = buffer.indexOf('\n');
            while (newlineIndex !== -1) {
                const line = buffer.slice(0, newlineIndex).trim();
                buffer = buffer.slice(newlineIndex + 1);
                if (line) yield JSON.parse(line);
                newlineIndex = buffer.indexOf('\n');
            }
        }

        buffer += decoder.decode();
        const trailing = buffer.trim();
        if (trailing) yield JSON.parse(trailing);
    } finally {
        try {
            await reader.cancel();
        } catch {
            // The reader is already closed; nothing to release.
        }
    }
}
