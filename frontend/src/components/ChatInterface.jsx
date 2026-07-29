import { useEffect, useRef, useState } from 'react';
import {
    Activity,
    AlertCircle,
    PanelLeftClose,
    PanelLeftOpen,
    PanelRightClose,
    PanelRightOpen,
    Send,
    Square,
    Trash2,
} from 'lucide-react';
import { useChatStore } from '../store';
import { LeftPanel, SidePanel, TypewriterText } from './AgentUI';

export const ChatInterface = () => {
    const {
        sessions,
        activeSessionId,
        isGenerating,
        leftPanelOpen,
        sidePanelOpen,
        toggleLeftPanel,
        toggleSidePanel,
        currentDraft,
        addMessage,
        updateActiveMessage,
        markMessageTyped,
        setCurrentDraft,
        setGenerating,
        clearAgentState,
        clearChat,
        addThinkingStep,
        setSources,
    } = useChatStore();

    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const activeSession =
        sessions.find((s) => s.id === activeSessionId) || sessions[0];
    const messages = activeSession?.messages || [];

    const scrollToBottom = () =>
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

    useEffect(() => {
        scrollToBottom();
    }, [messages, currentDraft]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || isGenerating) return;

        const userQuery = input;
        addMessage({
            role: 'user',
            content: userQuery,
            timestamp: new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
            }),
        });

        setInput('');
        setGenerating(true);
        clearAgentState();

        const assistantMsgId = Date.now() + 1;
        addMessage({
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            isNew: true,
            timestamp: new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
            }),
        });

        try {
            const response = await fetch('http://localhost:8000/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userQuery,
                    max_retries: 3,
                    top_k_retrieve: 15,
                    top_k_generate: 3,
                }),
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n').filter(Boolean);

                    for (const line of lines) {
                        const payload = JSON.parse(line);

                        if (payload.event === 'status') {
                            addThinkingStep({
                                type: 'status',
                                text: payload.message,
                            });
                        } else if (payload.event === 'sources') {
                            setSources(payload.data);
                        } else if (payload.event === 'token') {
                            setCurrentDraft((prev) => prev + payload.data);
                        } else if (payload.event === 'correction') {
                            addThinkingStep({
                                type: 'fail',
                                text: payload.message,
                            });
                            setCurrentDraft('');
                        } else if (payload.event === 'done') {
                            const trace = payload.trace;

                            if (trace.status === 'SUCCESS') {
                                updateActiveMessage(
                                    assistantMsgId,
                                    trace.final_answer,
                                    false
                                );
                            } else {
                                updateActiveMessage(assistantMsgId, '', true);
                            }

                            setCurrentDraft('');
                            setGenerating(false);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream Error:', error);
            updateActiveMessage(
                assistantMsgId,
                'SYSTEM_ERROR: Connection failed.',
                true
            );
            setGenerating(false);
        }
    };

    return (
        <main className='flex h-screen shadow-none overflow-hidden bg-space-indigo-900'>
            <LeftPanel />

            <section className='flex-1 flex flex-col h-full min-w-0'>
                <header className='flex items-center justify-between px-6 py-4 bg-space-indigo-950 shrink-0 border-b border-[#162236]'>
                    <section className='flex items-center space-x-3'>
                        <button
                            onClick={toggleLeftPanel}
                            className='text-platinum-100 hover:text-platinum-200 transition-colors cursor-pointer'
                            title='Toggle History Panel'>
                            {leftPanelOpen ?
                                <PanelLeftClose className='w-4 h-4 text-punch-red-500' />
                            :   <PanelLeftOpen className='w-4 h-4' />}
                        </button>
                        <Activity className='w-5 h-5 text-punch-red-500' />
                        <h1 className='text-sm font-bold text-platinum-100 tracking-wider'>
                            Medical Sovereign RAG
                        </h1>
                    </section>

                    <section className='flex items-center space-x-3'>
                        <button
                            onClick={clearChat}
                            className='text-platinum-100 hover:text-punch-red-500 transition-colors cursor-pointer'
                            title='Clear Session Messages'>
                            <Trash2 className='w-4 h-4' />
                        </button>
                        <button
                            onClick={toggleSidePanel}
                            className='text-platinum-100 hover:text-platinum-200 transition-colors cursor-pointer'
                            title='Toggle Reasoning Panel'>
                            {sidePanelOpen ?
                                <PanelRightClose className='w-4 h-4 text-punch-red-500' />
                            :   <PanelRightOpen className='w-4 h-4' />}
                        </button>
                    </section>
                </header>

                <section className='flex-1 overflow-y-auto p-4 md:px-12 space-y-4 bg-space-indigo-900'>
                    {messages.map((msg, idx) => {
                        const isLast = idx === messages.length - 1;
                        const isUser = msg.role === 'user';

                        return (
                            <article
                                key={msg.id || idx}
                                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                                <section
                                    className={`max-w-xl md:max-w-2xl ${isUser ? 'items-end' : 'items-start'}`}>
                                    <section
                                        className={`px-4 py-3 text-platinum-100 rounded-md text-xs md:text-sm ${isUser ? 'bg-space-indigo-950' : 'bg-space-indigo-800'}`}>
                                        {!isUser && msg.failed ?
                                            <mark className='flex items-start space-x-2 text-punch-red-500 font-bold text-xs md:text-sm bg-transparent'>
                                                <AlertCircle className='w-4 h-4 text-punch-red-500 shrink-0 mt-0.5' />
                                                <span>
                                                    Could not verify clinical
                                                    answer in corpus after 3
                                                    attempts.
                                                </span>
                                            </mark>
                                        :   <>
                                                {!isUser &&
                                                    isLast &&
                                                    isGenerating &&
                                                    currentDraft && (
                                                        <p className='text-gray-400 text-xs md:text-sm leading-relaxed italic mb-2 inline-block'>
                                                            {currentDraft}
                                                            <span className='inline-block w-1.5 h-3 bg-punch-red-500 ml-1 animate-pulse align-middle' />
                                                        </p>
                                                    )}

                                                {!isUser && msg.content && (
                                                    <TypewriterText
                                                        text={msg.content}
                                                        isNew={msg.isNew}
                                                        onComplete={() =>
                                                            markMessageTyped(
                                                                msg.id
                                                            )
                                                        }
                                                    />
                                                )}

                                                {isUser && (
                                                    <p className='whitespace-pre-wrap leading-relaxed'>
                                                        {msg.content}
                                                    </p>
                                                )}
                                            </>
                                        }

                                        <time className='block text-[9px] font-mono mt-1.5 text-right text-platinum-300'>
                                            {msg.timestamp}
                                        </time>
                                    </section>
                                </section>
                            </article>
                        );
                    })}
                    <section
                        ref={messagesEndRef}
                        className='h-2'
                    />
                </section>

                <footer className='p-4 bg-space-indigo-950 shrink-0'>
                    <form
                        onSubmit={handleSend}
                        className='max-w-4xl mx-auto relative flex items-center bg-space-indigo-900 rounded-md transition-colors'>
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSend(e);
                                }
                            }}
                            placeholder='Enter clinical query...'
                            className='w-full bg-transparent text-platinum-100 pl-4 pr-8 py-4 focus:outline-none resize-none text-xs md:text-sm'
                        />
                        <button
                            type='submit'
                            disabled={isGenerating || !input.trim()}
                            className='absolute right-2 p-2 bg-blue-950 text-platinum-100 rounded disabled:opacity-30 cursor-pointer transition-colors'>
                            {isGenerating ?
                                <Square className='size-4 fill-current' />
                            :   <div className='flex items-center space-x-1'>
                                    <span className='text-sm font-bold'>
                                        Send
                                    </span>{' '}
                                    <Send className='size-3' />
                                </div>
                            }
                        </button>
                    </form>
                </footer>
            </section>

            <SidePanel />
        </main>
    );
};
