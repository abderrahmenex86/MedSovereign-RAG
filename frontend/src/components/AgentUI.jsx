import { useState } from 'react';
import {
    AlertCircle,
    ArrowUpRight,
    CheckCircle2,
    ChevronDown,
    FileSearch,
    FileText,
    ListFilter,
    MessageSquare,
    PenLine,
    Plus,
    Search,
    ShieldCheck,
    Stethoscope,
    Trash2,
    Waypoints,
    X,
} from 'lucide-react';
import { useChatStore } from '../store';
import { Badge, Button, Tabs } from './ui';
import { cn } from '../lib/utils';

export const BrandMark = ({ className }) => (
    <span
        className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-navy-800 text-white shadow-sm dark:bg-navy-600',
            className
        )}>
        <Stethoscope aria-hidden='true' className='h-[18px] w-[18px]' />
    </span>
);

export const Wordmark = () => (
    <div className='flex min-w-0 items-center gap-2.5'>
        <BrandMark />
        <span className='truncate text-[17px] font-semibold tracking-tight text-ink'>
            MedSovereign
        </span>
    </div>
);

export const Sidebar = ({ health }) => {
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

    const corpusLabel =
        health?.corpus_format === 'jsonl' ? 'Literature' : 'MedQuad';
    const statusLabel =
        health?.demo ?
            'Demo mode · sample evidence'
        :   health ? `${corpusLabel} · ${health.generator}`
        :   'API offline';

    return (
        <>
            <button
                type='button'
                aria-label='Dismiss consultations'
                onClick={toggleLeftPanel}
                className='fixed inset-0 z-30 bg-navy-900/20 backdrop-blur-[2px] md:hidden dark:bg-black/60'
            />

            <aside
                aria-label='Consultations'
                className='fixed inset-y-0 left-0 z-40 flex h-full w-[272px] shrink-0 flex-col border-r border-line bg-panel md:static md:z-auto'>
                <div className='flex h-16 shrink-0 items-center justify-between gap-2 border-b border-line px-4'>
                    <Wordmark />
                    <button
                        type='button'
                        onClick={toggleLeftPanel}
                        aria-label='Close consultations'
                        className='shrink-0 rounded-md p-1.5 text-muted hover:bg-surface hover:text-ink md:hidden'>
                        <X aria-hidden='true' className='h-4 w-4' />
                    </button>
                </div>

                <div className='px-3 pt-4'>
                    <Button
                        variant='primary'
                        onClick={createNewSession}
                        disabled={isGenerating}
                        className='w-full justify-start'>
                        <Plus aria-hidden='true' className='h-4 w-4' />
                        New consult
                    </Button>
                </div>

                <div className='mt-6 flex items-center justify-between px-4'>
                    <p className='text-[11px] font-medium text-muted'>
                        Recent consults
                    </p>
                    <span className='text-[10px] tabular-nums text-faint'>
                        {sessions.length}
                    </span>
                </div>

                <nav className='mt-2 flex-1 overflow-y-auto px-2 pb-3'>
                    <ul className='space-y-0.5'>
                        {sessions.map((session) => {
                            const isActive = session.id === activeSessionId;

                            return (
                                <li key={session.id}>
                                    <div
                                        className={cn(
                                            'group flex items-center rounded-lg transition-colors',
                                            isActive ?
                                                'bg-navy-50 text-ink'
                                            :   'text-ink-soft hover:bg-surface'
                                        )}>
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
                                            className='flex min-w-0 flex-1 items-center gap-2 px-3 py-2.5 text-left disabled:cursor-not-allowed'>
                                            <MessageSquare
                                                aria-hidden='true'
                                                className={cn(
                                                    'h-3.5 w-3.5 shrink-0',
                                                    isActive ?
                                                        'text-accent'
                                                    :   'text-faint'
                                                )}
                                            />
                                            <span className='truncate text-[12.5px] font-medium'>
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
                                            aria-label={`Delete ${session.title}`}
                                            className='mr-1 rounded-md p-1.5 text-faint opacity-100 transition-opacity hover:bg-panel hover:text-danger focus-visible:opacity-100 group-hover:opacity-100 disabled:cursor-not-allowed md:opacity-0'>
                                            <Trash2
                                                aria-hidden='true'
                                                className='h-3.5 w-3.5'
                                            />
                                        </button>
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                </nav>

                <div className='border-t border-line px-4 py-3'>
                    <div className='flex items-center gap-2'>
                        <span
                            aria-hidden='true'
                            className={cn(
                                'h-1.5 w-1.5 rounded-full',
                                health?.demo ?
                                    'bg-warning'
                                : health ? 'bg-success'
                                : 'bg-faint'
                            )}
                        />
                        <p
                            className='truncate text-[10.5px] text-muted'
                            title={
                                health?.corpus_documents ?
                                    `${health.corpus_documents.toLocaleString()} documents · ${health.generator_backend}`
                                :   'Start the API to connect'
                            }>
                            {statusLabel}
                        </p>
                    </div>
                    <p className='mt-1.5 text-[10px] text-faint'>
                        Private by design. Runs locally.
                    </p>
                    <p className='mt-1 text-[10px] leading-4 text-faint'>
                        Not a medical device. For research and demonstration
                        only.
                    </p>
                </div>
            </aside>
        </>
    );
};

const sourceTitle = (source) =>
    source.title || source.question || source.doc_id || 'Untitled source';

const sourceLabel = (source) => {
    if (!source.source) return 'Source';
    if (source.source === 'pubmed') return 'PubMed';
    return source.source.charAt(0).toUpperCase() + source.source.slice(1);
};

const citation = (source) =>
    source.pmid ? `PMID ${source.pmid}` : source.doc_id;

const stepIcon = (step) => {
    const text = step.text?.toLowerCase() || '';

    if (step.type === 'fail') return AlertCircle;
    if (text.includes('passed')) return CheckCircle2;
    if (text.includes('search')) return Search;
    if (text.includes('rerank')) return ListFilter;
    if (text.includes('draft')) return PenLine;
    if (text.includes('auditor') || text.includes('critique')) return ShieldCheck;
    return Waypoints;
};

const SourcesList = ({ sources }) => {
    if (!sources.length) {
        return (
            <div className='flex flex-col items-center px-6 py-14 text-center'>
                <span className='flex h-10 w-10 items-center justify-center rounded-full bg-surface text-faint ring-1 ring-line'>
                    <FileSearch aria-hidden='true' className='h-5 w-5' />
                </span>
                <p className='mt-3 text-[12.5px] font-medium text-ink'>
                    No sources yet
                </p>
                <p className='mt-1 max-w-[230px] text-[11.5px] leading-5 text-muted'>
                    Ask a question and the passages the answer was built from
                    will appear here.
                </p>
            </div>
        );
    }

    return (
        <ul className='divide-y divide-line'>
            {sources.map((source, index) => {
                const year = (source.published || '').slice(0, 4);

                return (
                    <li key={source.chunk_id || `${source.doc_id}-${index}`}>
                        <details className='group'>
                            <summary className='flex cursor-pointer list-none items-start gap-3 px-4 py-3.5 transition-colors hover:bg-surface/60'>
                                <span className='mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-50 text-[10.5px] font-semibold text-accent ring-1 ring-navy-100'>
                                    {index + 1}
                                </span>

                                <span className='min-w-0 flex-1'>
                                    <span className='block text-[12.5px] font-medium leading-5 text-ink group-open:text-ink'>
                                        {sourceTitle(source)}
                                    </span>
                                    <span className='mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[10.5px] text-muted'>
                                        <Badge variant='navy'>
                                            {sourceLabel(source)}
                                        </Badge>
                                        {year && <span>{year}</span>}
                                        <span className='font-mono text-[10px] text-faint'>
                                            {citation(source)}
                                        </span>
                                    </span>
                                </span>

                                <ChevronDown
                                    aria-hidden='true'
                                    className='mt-1 h-3.5 w-3.5 shrink-0 text-faint transition-transform group-open:rotate-180'
                                />
                            </summary>

                            <div className='px-4 pb-4 pl-[52px]'>
                                {source.section && (
                                    <p className='mb-1 text-[10px] font-semibold tracking-wide text-accent uppercase'>
                                        {source.section}
                                    </p>
                                )}
                                <p className='text-[12px] leading-6 text-ink-soft'>
                                    {source.text}
                                </p>

                                <div className='mt-2.5 flex items-center justify-between gap-2 text-[10px] text-faint'>
                                    {typeof source.rerank_score ===
                                    'number' ? (
                                        <span
                                            title='Cross-encoder relevance score'>
                                            Relevance{' '}
                                            {source.rerank_score.toFixed(1)}
                                        </span>
                                    ) : (
                                        <span />
                                    )}

                                    {source.url && (
                                        <a
                                            href={source.url}
                                            target='_blank'
                                            rel='noreferrer noopener'
                                            className='inline-flex items-center gap-1 font-medium text-accent hover:text-ink'>
                                            Open source
                                            <ArrowUpRight
                                                aria-hidden='true'
                                                className='h-3 w-3'
                                            />
                                        </a>
                                    )}
                                </div>
                            </div>
                        </details>
                    </li>
                );
            })}
        </ul>
    );
};

const ReasoningList = ({ steps }) => {
    if (!steps.length) {
        return (
            <div className='flex flex-col items-center px-6 py-14 text-center'>
                <span className='flex h-10 w-10 items-center justify-center rounded-full bg-surface text-faint ring-1 ring-line'>
                    <Waypoints aria-hidden='true' className='h-5 w-5' />
                </span>
                <p className='mt-3 text-[12.5px] font-medium text-ink'>
                    No reasoning trace
                </p>
                <p className='mt-1 max-w-[230px] text-[11.5px] leading-5 text-muted'>
                    Retrieval, drafting, and verification steps appear here as
                    the agent works.
                </p>
            </div>
        );
    }

    return (
        <ol aria-live='polite' className='space-y-3 px-4 py-4'>
            {steps.map((step, index) => {
                const Icon = stepIcon(step);
                const failed = step.type === 'fail';

                return (
                    <li
                        key={`${step.text}-${index}`}
                        className='flex items-start gap-2.5'>
                        <span
                            className={cn(
                                'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-panel ring-1',
                                failed ? 'ring-danger/30' : 'ring-line'
                            )}>
                            <Icon
                                aria-hidden='true'
                                className={cn(
                                    'h-2.5 w-2.5',
                                    failed ? 'text-danger' : 'text-accent'
                                )}
                            />
                        </span>
                        <p
                            className={cn(
                                'text-[11.5px] leading-5',
                                failed ? 'text-danger' : 'text-ink-soft'
                            )}>
                            {step.text}
                        </p>
                    </li>
                );
            })}
        </ol>
    );
};

export const EvidencePanel = () => {
    const {
        sessions,
        activeSessionId,
        sidePanelOpen,
        toggleSidePanel,
    } = useChatStore();
    const [tab, setTab] = useState('sources');

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
                aria-label='Dismiss evidence'
                onClick={toggleSidePanel}
                className='fixed inset-0 z-30 bg-navy-900/20 backdrop-blur-[2px] md:hidden dark:bg-black/60'
            />

            <aside
                aria-label='Evidence'
                className='fixed inset-y-0 right-0 z-40 flex h-full w-[88vw] max-w-sm shrink-0 flex-col border-l border-line bg-panel md:static md:z-auto md:w-[348px] md:max-w-none'>
                <div className='flex h-16 shrink-0 items-center justify-between border-b border-line px-4'>
                    <div className='flex items-center gap-2'>
                        <FileText
                            aria-hidden='true'
                            className='h-4 w-4 text-accent'
                        />
                        <h2 className='text-[13px] font-semibold text-ink'>
                            Evidence
                        </h2>
                    </div>
                    <button
                        type='button'
                        onClick={toggleSidePanel}
                        aria-label='Close evidence'
                        className='rounded-md p-1.5 text-muted hover:bg-surface hover:text-ink md:hidden'>
                        <X aria-hidden='true' className='h-4 w-4' />
                    </button>
                </div>

                <div className='border-b border-line px-4 py-3'>
                    <Tabs
                        value={tab}
                        onChange={setTab}
                        items={[
                            {
                                value: 'sources',
                                label: 'Sources',
                                count: validSources.length,
                            },
                            {
                                value: 'reasoning',
                                label: 'Reasoning',
                                count: currentThinking.length,
                            },
                        ]}
                        className='w-full'
                    />
                </div>

                <div className='flex-1 overflow-y-auto'>
                    {tab === 'sources' ?
                        <SourcesList sources={validSources} />
                    :   <ReasoningList steps={currentThinking} />}
                </div>
            </aside>
        </>
    );
};
