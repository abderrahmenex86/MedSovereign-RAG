import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
    ChevronRight,
    FileText,
    MessageSquare,
    Plus,
    Trash2,
    X,
} from 'lucide-react';
import { useChatStore } from '../store';

export const TypewriterText = ({ text, isNew, onComplete }) => {
    const [displayedText, setDisplayedText] = useState(isNew ? '' : text);

    useEffect(() => {
        if (!isNew) return setDisplayedText(text);
        if (!text) return;
        if (displayedText.length < text.length) {
            const timer = setTimeout(
                () =>
                    setDisplayedText(
                        text.substring(0, displayedText.length + 1)
                    ),
                10
            );
            return () => clearTimeout(timer);
        } else if (onComplete) {
            onComplete();
        }
    }, [text, displayedText, isNew]);

    return (
        <section className='prose prose-invert prose-teal max-w-none text-xs md:text-sm text-platinum-100 leading-relaxed'>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    p: ({ children }) => <p className='inline'>{children}</p>,
                }}>
                {displayedText}
            </ReactMarkdown>
            {isNew && displayedText.length < text.length && (
                <span className='inline-block w-1.5 h-3 bg-punch-red-500 ml-1 animate-pulse align-middle' />
            )}
        </section>
    );
};

export const LeftPanel = () => {
    const {
        sessions,
        activeSessionId,
        leftPanelOpen,
        createNewSession,
        switchSession,
        deleteSession,
        isGenerating,
    } = useChatStore();

    if (!leftPanelOpen) return null;

    return (
        <aside className='w-64 bg-space-indigo-950 flex flex-col h-full z-20 shrink-0 font-mono text-xs border-r border-[#162236]'>
            <header className='px-6 py-3'>
                <button
                    onClick={createNewSession}
                    disabled={isGenerating}
                    className='w-full flex items-center justify-center space-x-2 py-1 px-3 bg-[#131d33] hover:bg-[#1a2b4c] text-platinum-100 rounded border border-[#1e2c47] cursor-pointer transition-colors disabled:opacity-30'>
                    <Plus className='size-4 text-punch-red-500' />
                    <span className='font-bold text-xs md:text-sm tracking-wider'>
                        New session
                    </span>
                </button>
            </header>

            <nav className='flex-1 overflow-y-auto p-2 space-y-1'>
                <ul className='space-y-1'>
                    {sessions.map((session) => {
                        const isActive = session.id === activeSessionId;
                        return (
                            <li key={session.id}>
                                <article
                                    onClick={() =>
                                        !isGenerating &&
                                        switchSession(session.id)
                                    }
                                    className={`group flex items-center justify-between p-2.5 rounded cursor-pointer transition-colors border ${
                                        isActive ?
                                            'bg-[#131d33] text-platinum-100 border-[#1e2c47]'
                                        :   'text-gray-400 hover:bg-[#0d1424] hover:text-platinum-200 border-transparent'
                                    }`}>
                                    <section className='flex items-center space-x-2 truncate pr-1'>
                                        <MessageSquare
                                            className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-punch-red-500' : 'text-gray-600'}`}
                                        />
                                        <span className='truncate text-[11px]'>
                                            {session.title}
                                        </span>
                                    </section>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (!isGenerating)
                                                deleteSession(session.id);
                                        }}
                                        className='opacity-0 group-hover:opacity-100 text-gray-500 hover:text-punch-red-500 transition-opacity p-0.5 cursor-pointer'>
                                        <Trash2 className='w-3 h-3' />
                                    </button>
                                </article>
                            </li>
                        );
                    })}
                </ul>
            </nav>
        </aside>
    );
};

export const SidePanel = () => {
    const { sessions, activeSessionId, sidePanelOpen, toggleSidePanel } =
        useChatStore();

    if (!sidePanelOpen) return null;

    const activeSession =
        sessions.find((s) => s.id === activeSessionId) || sessions[0];
    const currentThinking = activeSession?.currentThinking || [];
    const currentSources = activeSession?.currentSources || [];

    const validSources =
        currentSources?.filter(
            (s) =>
                s.text &&
                !s.text.includes('CONTEXT_MISSING') &&
                !s.text.includes('No context retrieved.')
        ) || [];

    return (
        <aside className='w-80 md:w-96 bg-space-indigo-950 flex flex-col h-full z-20 shrink-0 font-mono text-xs border-l border-[#162236]'>
            <header className='flex items-center justify-between px-6 py-4 border-b border-[#162236]'>
                <h2 className='font-bold text-platinum-100 tracking-wider text-sm'>
                    Agentic Trace Panel
                </h2>
                <button
                    onClick={toggleSidePanel}
                    className='text-platinum-100 hover:text-punch-red-500 transition-colors cursor-pointer'>
                    <X className='size-4' />
                </button>
            </header>

            <section className='flex-1 overflow-y-auto p-4 space-y-6'>
                <section>
                    {currentThinking.length === 0 ?
                        <p className='text-gray-600 italic text-[11px]'>
                            No active reasoning trace.
                        </p>
                    :   <ul className='space-y-2'>
                            {currentThinking.map((step, idx) => (
                                <li
                                    key={idx}
                                    className='flex items-start space-x-2 text-gray-400 bg-[#070b14] p-2 rounded border border-[#162236]'>
                                    <ChevronRight className='w-3 h-3 text-punch-red-500 shrink-0 mt-0.5' />
                                    <span
                                        className={
                                            step.type === 'fail' ?
                                                'text-punch-red-400'
                                            :   'text-platinum-300'
                                        }>
                                        {step.text}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    }
                </section>

                <section>
                    {validSources.length === 0 ?
                        <p className='text-platinum-300 italic text-[11px]'>
                            No sources loaded.
                        </p>
                    :   <ul className='space-y-2'>
                            {validSources.map((src, i) => (
                                <li
                                    key={i}
                                    className='bg-[#070b14] p-2.5 rounded border border-[#162236]'>
                                    <details className='group'>
                                        <summary className='cursor-pointer flex items-center justify-between text-red-400 font-bold text-[10px] select-none'>
                                            <span className='flex items-center'>
                                                <FileText className='w-3 h-3 mr-1' />{' '}
                                                {src.doc_id}
                                            </span>
                                            <span className='text-gray-600 group-open:rotate-90 transition-transform'>
                                                ►
                                            </span>
                                        </summary>
                                        <p className='mt-2 text-gray-400 text-[10px] leading-relaxed border-t border-[#162236] pt-2'>
                                            {src.text}
                                        </p>
                                    </details>
                                </li>
                            ))}
                        </ul>
                    }
                </section>
            </section>
        </aside>
    );
};
