import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export const CHAT_STORAGE_KEY = 'medsovereign-v3-storage';

const uid = () =>
    typeof crypto !== 'undefined' && crypto.randomUUID ?
        crypto.randomUUID()
    :   `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const newSession = () => ({
    id: uid(),
    title: 'New consultation',
    titleLocked: false,
    messages: [],
    currentThinking: [],
    currentSources: [],
});

const initialSession = newSession();

const normalizeTitle = (title) => {
    if (typeof title !== 'string') return 'New consultation';

    const cleaned = title.trim().replace(/\s+/g, ' ');
    if (!cleaned) return 'New consultation';
    if (cleaned === 'New Clinical Query') return 'New consultation';
    return cleaned.slice(0, 40);
};

const normalizeMessage = (message) => ({
    id: message?.id ?? uid(),
    role: message?.role === 'user' ? 'user' : 'assistant',
    content: typeof message?.content === 'string' ? message.content : '',
    timestamp: typeof message?.timestamp === 'string' ? message.timestamp : '',
    failed: Boolean(message?.failed),
    error: typeof message?.error === 'string' ? message.error : null,
    attempts: Number.isInteger(message?.attempts) ? message.attempts : null,
});

const normalizeSession = (session) => ({
    id: session?.id ?? uid(),
    title: normalizeTitle(session?.title),
    titleLocked: Boolean(session?.titleLocked),
    messages: Array.isArray(session?.messages) ?
        session.messages.map(normalizeMessage)
    :   [],
    currentThinking: Array.isArray(session?.currentThinking) ?
        session.currentThinking.filter((step) => step && step.text)
    :   [],
    currentSources: Array.isArray(session?.currentSources) ?
        session.currentSources.filter(Boolean)
    :   [],
});

const updateSession = (state, sessionId, updater) => ({
    sessions: state.sessions.map((session) =>
        session.id === sessionId ? updater(session) : session
    ),
});

const isDesktop = () =>
    typeof window === 'undefined' ? true : (
        window.matchMedia('(min-width: 768px)').matches
    );

export const useChatStore = create(
    persist(
        (set) => ({
            sessions: [initialSession],
            activeSessionId: initialSession.id,
            isGenerating: false,
            leftPanelOpen: isDesktop(),
            sidePanelOpen: isDesktop(),
            currentDraft: '',
            theme: 'light',

            toggleLeftPanel: () =>
                set((state) => ({ leftPanelOpen: !state.leftPanelOpen })),
            toggleSidePanel: () =>
                set((state) => ({ sidePanelOpen: !state.sidePanelOpen })),
            toggleTheme: () =>
                set((state) => ({
                    theme: state.theme === 'dark' ? 'light' : 'dark',
                })),
            setGenerating: (value) => set({ isGenerating: value }),
            setCurrentDraft: (text) => set({ currentDraft: text }),
            appendDraft: (text) =>
                set((state) => ({ currentDraft: state.currentDraft + text })),

            createNewSession: () =>
                set((state) => {
                    const session = newSession();
                    return {
                        sessions: [session, ...state.sessions],
                        activeSessionId: session.id,
                        currentDraft: '',
                    };
                }),

            switchSession: (id) =>
                set({ activeSessionId: id, currentDraft: '' }),

            deleteSession: (id) =>
                set((state) => {
                    const remaining = state.sessions.filter(
                        (session) => session.id !== id
                    );
                    const sessions = remaining.length ? remaining : [newSession()];

                    return {
                        sessions,
                        activeSessionId:
                            state.activeSessionId === id ?
                                sessions[0].id
                            :   state.activeSessionId,
                        currentDraft: '',
                    };
                }),

            addMessage: (sessionId, message) =>
                set((state) =>
                    updateSession(state, sessionId, (session) => {
                        const isFirstUserMessage =
                            session.messages.length === 0 &&
                            message.role === 'user';
                        const content =
                            typeof message.content === 'string' ?
                                message.content
                            :   '';

                        return {
                            ...session,
                            title:
                                isFirstUserMessage && !session.titleLocked ?
                                    normalizeTitle(content.slice(0, 40))
                                :   session.title,
                            messages: [
                                ...session.messages,
                                normalizeMessage({
                                    ...message,
                                    content,
                                }),
                            ],
                        };
                    })
                ),

            renameSession: (sessionId, title) =>
                set((state) =>
                    updateSession(state, sessionId, (session) => ({
                        ...session,
                        title: normalizeTitle(title),
                        titleLocked: true,
                    }))
                ),

            applyGeneratedTitle: (sessionId, title) =>
                set((state) =>
                    updateSession(state, sessionId, (session) =>
                        session.titleLocked ?
                            session
                        :   {
                                ...session,
                                title: normalizeTitle(title),
                            }
                    )
                ),

            updateMessage: (sessionId, messageId, patch) =>
                set((state) =>
                    updateSession(state, sessionId, (session) => ({
                        ...session,
                        messages: session.messages.map((message) =>
                            message.id === messageId ?
                                { ...message, ...patch }
                            :   message
                        ),
                    }))
                ),

            addThinkingStep: (sessionId, step) =>
                set((state) =>
                    updateSession(state, sessionId, (session) => ({
                        ...session,
                        currentThinking: [...session.currentThinking, step],
                    }))
                ),

            setSources: (sessionId, sources) =>
                set((state) =>
                    updateSession(state, sessionId, (session) => ({
                        ...session,
                        currentSources: sources,
                    }))
                ),

            clearAgentState: (sessionId) =>
                set((state) => ({
                    currentDraft: '',
                    ...updateSession(state, sessionId, (session) => ({
                        ...session,
                        currentThinking: [],
                        currentSources: [],
                    })),
                })),

            clearChat: (sessionId) =>
                set((state) => ({
                    currentDraft: '',
                    ...updateSession(state, sessionId, (session) => ({
                        ...session,
                        messages: [],
                        currentThinking: [],
                        currentSources: [],
                    })),
                })),
        }),
        {
            name: CHAT_STORAGE_KEY,
            // Conversations, titles, and theme live in localStorage. Only the
            // in-flight draft and generating flag are deliberately excluded.
            storage: createJSONStorage(() => localStorage),
            version: 2,
            migrate: (persisted) => persisted,
            partialize: (state) => ({
                sessions: state.sessions,
                activeSessionId: state.activeSessionId,
                leftPanelOpen: state.leftPanelOpen,
                sidePanelOpen: state.sidePanelOpen,
                theme: state.theme,
            }),
            merge: (persisted, current) => {
                const storedSessions = Array.isArray(persisted?.sessions) ?
                    persisted.sessions.filter(Boolean).map(normalizeSession)
                :   [];

                const sessions = (
                    storedSessions.length ? storedSessions : current.sessions
                ).map((session) => ({
                    ...session,
                    // An empty assistant message means the tab was reloaded or
                    // closed mid-request. Show that instead of a blank bubble.
                    messages: session.messages.map((message) =>
                        message.role === 'assistant' &&
                        !message.content &&
                        !message.failed ?
                            {
                                ...message,
                                failed: true,
                                error: 'Generation was interrupted by a reload.',
                            }
                        :   message
                    ),
                }));

                const activeSessionId = sessions.some(
                    (session) => session.id === persisted?.activeSessionId
                ) ?
                    persisted.activeSessionId
                :   sessions[0].id;

                return {
                    ...current,
                    sessions,
                    activeSessionId,
                    leftPanelOpen:
                        isDesktop() ?
                            (persisted?.leftPanelOpen ??
                            current.leftPanelOpen)
                        :   false,
                    sidePanelOpen:
                        isDesktop() ?
                            (persisted?.sidePanelOpen ??
                            current.sidePanelOpen)
                        :   false,
                    theme: persisted?.theme === 'dark' ? 'dark' : 'light',
                    // Transient state must never be rehydrated: a reload while
                    // a request was in flight would otherwise disable the UI.
                    isGenerating: false,
                    currentDraft: '',
                };
            },
        }
    )
);
