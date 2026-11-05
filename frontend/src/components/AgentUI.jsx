import { ChevronRight, FileText, MessageSquare, Plus, Trash2, X } from 'lucide-react';
import { useChatStore } from '../store';

export const LeftPanel = () => {
    const {
        sessions,
        activeSessionId,
        leftPanelOpen,
        createNewSession,
        switchSession,
        deleteSession,
        toggleLeftPanel,
        isGenerating,
    } = useChatStore();

    if (!leftPanelOpen) return null;

    return (
        <>
            <button
                type='button'
                aria-label='Close history panel'
                onClick={toggleLeftPanel}
                className='fixed inset-0 z-30 bg-black/60 md:hidden'
            />

            <aside
                aria-label='Session history'
                className='fixed inset-y-0 left-0 z-40 flex h-full w-64 shrink-0 flex-col border-r border-[#162236] bg-space-indigo-950 font-mono text-xs md:static md:z-auto'>
                <header className='flex items-center justify-between px-4 py-3'>
                    <button
                        type='button'
                        onClick={createNewSession}
                        disabled={isGenerating}
                        className='flex flex-1 items-center justify-center space-x-2 rounded border border-[#1e2c47] bg-[#131d33] px-3 py-1.5 text-platinum-100 transition-colors hover:bg-[#1a2b4c] disabled:cursor-not-allowed disabled:opacity-30'>
                        <Plus className='size-4 text-punch-red-500' aria-hidden='true' />
                        <span className='text-xs font-bold tracking-wider md:text-sm'>
                            New session
                        </span>
                    </button>
                    <button
                        type='button'
                        onClick={toggleLeftPanel}
                        aria-label='Close history panel'
                        className='ml-2 rounded p-1.5 text-platinum-200 transition-colors hover:text-punch-red-400 focus-visible:outline-2 md:hidden'>
                        <X className='size-4' aria-hidden='true' />
                    </button>
                </header>

                <nav className='flex-1 overflow-y-auto p-2'>
                    <ul className='space-y-1'>
                        {sessions.map((session) => {
                            const isActive = session.id === activeSessionId;

                            return (
                                <li key={session.id}>
                                    <div
                                        className={`group flex items-center rounded border transition-colors ${
                                            isActive ?
                                                'border-[#1e2c47] bg-[#131d33] text-platinum-100'
                                            :   'border-transparent text-platinum-300 hover:bg-[#0d1424] hover:text-platinum-200'
                                        }`}>
                                        <button
                                            type='button'
                                            onClick={() =>
                                                !isGenerating &&
                                                switchSession(session.id)
                                            }
                                            disabled={isGenerating}
                                            aria-current={
                                                isActive ? 'page' : undefined
                                            }
                                            className='flex min-w-0 flex-1 items-center gap-2 p-2.5 text-left disabled:cursor-not-allowed'>
                                            <MessageSquare
                                                aria-hidden='true'
                                                className={`h-3.5 w-3.5 shrink-0 ${
                                                    isActive ?
                                                        'text-punch-red-500'
                                                    :   'text-platinum-500'
                                                }`}
                                            />
                                            <span className='truncate text-[11px]'>
                                                {session.title}
                                            </span>
                                        </button>
                                        <button
                                            type='button'
                                            onClick={() =>
                                                !isGenerating &&
                                                deleteSession(session.id)
                                            }
                                            disabled={isGenerating}
                                            aria-label={`Delete session "${session.title}"`}
                                            className='p-2.5 text-platinum-500 opacity-100 transition-opacity hover:text-punch-red-500 disabled:cursor-not-allowed md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100'>
                                            <Trash2
                                                className='h-3.5 w-3.5'
                                                aria-hidden='true'
                                            />
                                        </button>
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                </nav>
            </aside>
        </>
    );
};

export const SidePanel = () => {
    const {
        sessions,
        activeSessionId,
        sidePanelOpen,
        toggleSidePanel,
    } = useChatStore();

    if (!sidePanelOpen) return null;

    const activeSession =
        sessions.find((session) => session.id === activeSessionId) ||
        sessions[0];
    const currentThinking = activeSession?.currentThinking || [];
    const currentSources = activeSession?.currentSources || [];

    const validSources = currentSources.filter(
        (source) =>
            source?.text &&
            !source.text.includes('CONTEXT_MISSING') &&
            !source.text.includes('No context retrieved.')
    );

    return (
        <>
            <button
                type='button'
                aria-label='Close reasoning panel'
                onClick={toggleSidePanel}
                className='fixed inset-0 z-30 bg-black/60 md:hidden'
            />

            <aside
                aria-label='Agentic trace'
                className='fixed inset-y-0 right-0 z-40 flex h-full w-80 max-w-[85vw] shrink-0 flex-col border-l border-[#162236] bg-space-indigo-950 font-mono text-xs md:static md:z-auto md:w-96 md:max-w-none'>
                <header className='flex items-center justify-between border-b border-[#162236] px-6 py-4'>
                    <h2 className='text-sm font-bold tracking-wider text-platinum-100'>
                        Agentic Trace
                    </h2>
                    <button
                        type='button'
                        onClick={toggleSidePanel}
                        aria-label='Close reasoning panel'
                        className='rounded p-1 text-platinum-200 transition-colors hover:text-punch-red-400'>
                        <X className='size-4' aria-hidden='true' />
                    </button>
                </header>

                <div className='flex-1 space-y-6 overflow-y-auto p-4'>
                    <section aria-labelledby='reasoning-heading'>
                        <h3
                            id='reasoning-heading'
                            className='mb-2 text-[11px] font-semibold uppercase tracking-wider text-platinum-400'>
                            Reasoning
                        </h3>

                        {currentThinking.length === 0 ?
                            <p className='text-[11px] text-platinum-400 italic'>
                                No active reasoning trace.
                            </p>
                        :   <ol
                                aria-live='polite'
                                className='space-y-2'>
                                {currentThinking.map((step, index) => (
                                    <li
                                        key={`${step.text}-${index}`}
                                        className='flex items-start space-x-2 rounded border border-[#162236] bg-[#070b14] p-2 text-platinum-300'>
                                        <ChevronRight
                                            aria-hidden='true'
                                            className='mt-0.5 h-3 w-3 shrink-0 text-punch-red-500'
                                        />
                                        <span
                                            className={
                                                step.type === 'fail' ?
                                                    'text-punch-red-300'
                                                :   'text-platinum-200'
                                            }>
                                            {step.text}
                                        </span>
                                    </li>
                                ))}
                            </ol>
                        }
                    </section>

                    <section aria-labelledby='sources-heading'>
                        <h3
                            id='sources-heading'
                            className='mb-2 text-[11px] font-semibold uppercase tracking-wider text-platinum-400'>
                            Sources
                        </h3>

                        {validSources.length === 0 ?
                            <p className='text-[11px] text-platinum-400 italic'>
                                No sources loaded.
                            </p>
                        :   <ul className='space-y-2'>
                                {validSources.map((source, index) => (
                                    <li
                                        key={source.chunk_id || `${source.doc_id}-${index}`}
                                        className='rounded border border-[#162236] bg-[#070b14] p-2.5'>
                                        <details className='group'>
                                            <summary className='flex cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-bold text-punch-red-300 select-none'>
                                                <span className='flex min-w-0 items-center gap-1'>
                                                    <FileText
                                                        aria-hidden='true'
                                                        className='h-3 w-3 shrink-0'
                                                    />
                                                    <span className='truncate'>
                                                        {source.question || source.doc_id}
                                                    </span>
                                                </span>
                                                <span className='flex shrink-0 items-center gap-1 text-platinum-400'>
                                                    <span className='text-[10px] font-normal'>
                                                        {source.doc_id}
                                                    </span>
                                                    <span
                                                        aria-hidden='true'
                                                        className='transition-transform group-open:rotate-90'>
                                                        ►
                                                    </span>
                                                </span>
                                            </summary>
                                            <p className='mt-2 border-t border-[#162236] pt-2 text-[11px] leading-relaxed text-platinum-300'>
                                                {source.text}
                                            </p>
                                            {typeof source.rerank_score ===
                                                'number' && (
                                                <p className='mt-1 text-[10px] text-platinum-500'>
                                                    rerank score:{' '}
                                                    {source.rerank_score.toFixed(2)}
                                                </p>
                                            )}
                                        </details>
                                    </li>
                                ))}
                            </ul>
                        }
                    </section>
                </div>
            </aside>
        </>
    );
};
