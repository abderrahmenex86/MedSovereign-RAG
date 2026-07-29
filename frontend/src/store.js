import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useChatStore = create(
    persist(
        (set, get) => ({
            sessions: [
                {
                    id: 1,
                    title: 'New Clinical Query',
                    messages: [],
                    currentThinking: [],
                    currentSources: [],
                },
            ],
            activeSessionId: 1,
            isGenerating: false,
            leftPanelOpen: true,
            sidePanelOpen: true,
            currentDraft: '',

            toggleLeftPanel: () =>
                set((s) => ({ leftPanelOpen: !s.leftPanelOpen })),
            toggleSidePanel: () =>
                set((s) => ({ sidePanelOpen: !s.sidePanelOpen })),
            setGenerating: (val) => set({ isGenerating: val }),
            setCurrentDraft: (text) => set({ currentDraft: text }),

            createNewSession: () =>
                set((state) => {
                    const newSession = {
                        id: Date.now(),
                        title: 'New Clinical Query',
                        messages: [],
                        currentThinking: [],
                        currentSources: [],
                    };
                    return {
                        sessions: [newSession, ...state.sessions],
                        activeSessionId: newSession.id,
                        currentDraft: '',
                    };
                }),

            switchSession: (id) =>
                set({ activeSessionId: id, currentDraft: '' }),

            deleteSession: (id) =>
                set((state) => {
                    const filtered = state.sessions.filter((s) => s.id !== id);
                    const fallback =
                        filtered.length ? filtered : (
                            [
                                {
                                    id: Date.now(),
                                    title: 'New Clinical Query',
                                    messages: [],
                                    currentThinking: [],
                                    currentSources: [],
                                },
                            ]
                        );
                    return {
                        sessions: fallback,
                        activeSessionId: fallback[0].id,
                        currentDraft: '',
                    };
                }),

            addMessage: (msg) =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        sessions: state.sessions.map((s) => {
                            if (s.id !== activeId) return s;
                            const isFirstUserMsg =
                                s.messages.length === 0 && msg.role === 'user';
                            return {
                                ...s,
                                title:
                                    isFirstUserMsg ?
                                        msg.content.slice(0, 26) +
                                        (msg.content.length > 26 ? '...' : '')
                                    :   s.title,
                                messages: [
                                    ...s.messages,
                                    { ...msg, id: Date.now() },
                                ],
                            };
                        }),
                    };
                }),

            updateActiveMessage: (msgId, content, failed = false) =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                {
                                    ...s,
                                    messages: s.messages.map((m) =>
                                        m.id === msgId ?
                                            {
                                                ...m,
                                                content,
                                                failed,
                                                isNew: true,
                                            }
                                        :   m
                                    ),
                                }
                            :   s
                        ),
                    };
                }),

            markMessageTyped: (msgId) =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                {
                                    ...s,
                                    messages: s.messages.map((m) =>
                                        m.id === msgId ?
                                            { ...m, isNew: false }
                                        :   m
                                    ),
                                }
                            :   s
                        ),
                    };
                }),

            addThinkingStep: (step) =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                {
                                    ...s,
                                    currentThinking: [
                                        ...s.currentThinking,
                                        step,
                                    ],
                                }
                            :   s
                        ),
                    };
                }),

            setSources: (sources) =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                { ...s, currentSources: sources }
                            :   s
                        ),
                    };
                }),

            clearAgentState: () =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        currentDraft: '',
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                {
                                    ...s,
                                    currentThinking: [],
                                    currentSources: [],
                                }
                            :   s
                        ),
                    };
                }),

            clearChat: () =>
                set((state) => {
                    const activeId =
                        state.activeSessionId || state.sessions[0].id;
                    return {
                        currentDraft: '',
                        sessions: state.sessions.map((s) =>
                            s.id === activeId ?
                                {
                                    ...s,
                                    messages: [],
                                    currentThinking: [],
                                    currentSources: [],
                                }
                            :   s
                        ),
                    };
                }),
        }),
        {
            name: 'medsovereign-session-storage',
        }
    )
);
