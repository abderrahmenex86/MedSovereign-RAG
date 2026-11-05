const DEFAULT_API_URL = 'http://localhost:8000';
const env = import.meta.env || {};

export const API_URL = (env.VITE_API_URL || DEFAULT_API_URL).replace(
    /\/+$/,
    ''
);

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

/**
 * Stream NDJSON events from the backend.
 *
 * The network does not preserve write boundaries, so a JSON object can arrive
 * split across two reads. Everything is buffered until a newline proves the
 * line is complete; parsing per-chunk loses answers at random.
 */
export async function* streamQuery(payload, { signal } = {}) {
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
