import { useEffect, useRef, useState } from 'react';
import {
    AlertCircle,
    ArrowUpRight,
    Check,
    Copy,
    FileText,
    Menu,
    Moon,
    PanelLeft,
    Pencil,
    Send,
    Square,
    Stethoscope,
    Sun,
    Trash2,
} from 'lucide-react';
import { flushSync } from 'react-dom';
import { useChatStore } from '../store';
import {
    fetchHealth,
    cancelRequest,
    streamQuery,
    DEMO_MODE,
} from '../lib/api';
import { BrandMark, EvidencePanel, Sidebar } from './AgentUI';
import { Markdown } from './Markdown';
import { Badge, Button, Spinner } from './ui';
import { cn } from '../lib/utils';

const SUGGESTIONS = [
    'What are the first-line treatments for acute bronchitis?',
    'How is newly diagnosed type 2 diabetes managed?',
    'What are the red flags in acute low back pain?',
    'When is antibiotic prophylaxis indicated before dental procedures?',
];

const newMessageId = () =>
    typeof crypto !== 'undefined' && crypto.randomUUID ?
        crypto.randomUUID()
    :   String(Date.now());

const now = () =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const EMPTY_MESSAGES = [];

const FailureNotice = ({ error, attempts }) => {
    const stopped = error === 'Generation stopped.';
    const message =
        error ||
        `The answer could not be verified against the retrieved sources after ${
            attempts ?? 'the maximum number of'
        } attempt(s).`;

    return (
        <div
            role='alert'
            className={cn(
                'flex items-start gap-2 rounded-lg border p-3 text-[12px] leading-5',
                stopped ?
                    'border-warning/20 bg-warning-soft text-warning'
                :   'border-danger/15 bg-danger-soft text-danger'
            )}>
            <AlertCircle
                aria-hidden='true'
                className='mt-0.5 h-4 w-4 shrink-0'
            />
            <span>{message}</span>
        </div>
    );
};

const CopyButton = ({ text }) => {
    const [copied, setCopied] = useState(false);
    const timerRef = useRef(null);

    useEffect(() => () => clearTimeout(timerRef.current), []);

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            timerRef.current = setTimeout(() => setCopied(false), 1600);
        } catch {
            // Clipboard access can be denied; the answer is still selectable.
        }
    };

    return (
        <button
            type='button'
            onClick={copy}
            aria-label={copied ? 'Answer copied' : 'Copy answer'}
            title={copied ? 'Copied' : 'Copy answer'}
            className='rounded-md p-1.5 text-faint opacity-60 transition-opacity hover:bg-surface hover:text-ink focus-visible:opacity-100 group-hover:opacity-100 md:opacity-0'>
            {copied ?
                <Check aria-hidden='true' className='h-3.5 w-3.5 text-success' />
            :   <Copy aria-hidden='true' className='h-3.5 w-3.5' />}
        </button>
    );
};

const EditableTitle = ({ title, onSave, className }) => {
    const [editing, setEditing] = useState(false);
    const [value, setValue] = useState(title);
    const inputRef = useRef(null);

    useEffect(() => {
        if (editing) inputRef.current?.select();
    }, [editing]);

    const startEditing = () => {
        setValue(title);
        setEditing(true);
    };

    const commit = () => {
        const next = value.trim().replace(/\s+/g, ' ').slice(0, 40);
        if (next) onSave(next);
        else setValue(title);
        setEditing(false);
    };

    if (editing) {
        return (
            <input
                ref={inputRef}
                value={value}
                maxLength={40}
                aria-label='Consultation title'
                onChange={(event) => setValue(event.target.value)}
                onBlur={commit}
                onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        commit();
                    } else if (event.key === 'Escape') {
                        setValue(title);
                        setEditing(false);
                    }
                }}
                className={cn(
                    'min-w-0 flex-1 rounded-md border border-navy-200 bg-panel px-2 py-1 text-[13px] font-medium text-ink outline-none focus:ring-2 focus:ring-navy-100',
                    className
                )}
            />
        );
    }

    return (
        <button
            type='button'
            onClick={startEditing}
            title='Rename consultation'
            className='group flex min-w-0 flex-1 items-center gap-1.5 text-left'>
            <span
                className={cn('truncate font-medium text-ink', className)}>
                {title}
            </span>
            <Pencil
                aria-hidden='true'
                className='h-3 w-3 shrink-0 text-faint opacity-40 transition-opacity group-hover:opacity-100'
            />
        </button>
    );
};

const EmptyState = ({ onAsk }) => (
    <div className='mx-auto max-w-2xl pt-6 md:pt-14'>
        <div className='text-center'>
            <span className='mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-navy-800 text-white shadow-sm dark:bg-navy-600'>
                <Stethoscope aria-hidden='true' className='h-6 w-6' />
            </span>
            <h2 className='mt-5 text-[26px] font-semibold leading-[1.2] tracking-[-0.02em] text-ink md:text-[28px]'>
                Ask the evidence.
            </h2>
            <p className='mx-auto mt-3 max-w-md text-[13px] leading-6 text-muted'>
                Grounded answers with sources you can open. Every claim is
                checked against the retrieved passages.
            </p>
        </div>

        <div className='mt-8 grid gap-2 sm:grid-cols-2'>
            {SUGGESTIONS.map((question) => (
                <button
                    key={question}
                    type='button'
                    onClick={() => onAsk(question)}
                    className='group flex items-start justify-between gap-3 rounded-xl border border-line bg-panel p-3.5 text-left transition-colors hover:border-navy-200 hover:bg-navy-50/40'>
                    <span className='text-[12px] leading-5 text-ink-soft'>
                        {question}
                    </span>
                    <ArrowUpRight
                        aria-hidden='true'
                        className='mt-0.5 h-4 w-4 shrink-0 text-faint transition-colors group-hover:text-accent'
                    />
                </button>
            ))}
        </div>
    </div>
);

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
        updateMessage,
        setCurrentDraft,
        appendDraft,
        setGenerating,
        clearAgentState,
        clearChat,
        addThinkingStep,
        setSources,
        renameSession,
        applyGeneratedTitle,
        theme,
        toggleTheme,
    } = useChatStore();

    const [input, setInput] = useState('');
    const [liveStatus, setLiveStatus] = useState('');
    const [health, setHealth] = useState(null);
    const controllerRef = useRef(null);
    const activeRequestIdRef = useRef(null);
    const transcriptRef = useRef(null);
    const textareaRef = useRef(null);
    const stickToBottomRef = useRef(true);

    const activeSession =
        sessions.find((session) => session.id === activeSessionId) ||
        sessions[0];
    const messages = activeSession?.messages || EMPTY_MESSAGES;
    const sources = activeSession?.currentSources || [];
    const validSourceCount = sources.filter(
        (source) => source?.text && !source.text.includes('CONTEXT_MISSING')
    ).length;

    useEffect(() => {
        document.documentElement.classList.toggle('dark', theme === 'dark');
    }, [theme]);

    useEffect(() => {
        const controller = new AbortController();

        fetchHealth({ signal: controller.signal })
            .then(setHealth)
            .catch(() => setHealth(null));

        return () => controller.abort();
    }, []);

    useEffect(() => {
        const transcript = transcriptRef.current;
        if (transcript && stickToBottomRef.current) {
            transcript.scrollTop = transcript.scrollHeight;
        }
    }, [messages, currentDraft]);

    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }, [input]);

    const handleScroll = () => {
        const transcript = transcriptRef.current;
        if (!transcript) return;
        stickToBottomRef.current =
            transcript.scrollHeight -
                transcript.scrollTop -
                transcript.clientHeight <
            100;
    };

    const handleStop = () => {
        controllerRef.current?.abort();
        cancelRequest(activeRequestIdRef.current);
    };

    const handleThemeToggle = (event) => {
        const nextTheme = theme === 'dark' ? 'light' : 'dark';
        const reduceMotion = window.matchMedia(
            '(prefers-reduced-motion: reduce)'
        ).matches;

        const applyTheme = () => {
            document.documentElement.classList.toggle(
                'dark',
                nextTheme === 'dark'
            );
            flushSync(() => toggleTheme());
        };

        if (!document.startViewTransition || reduceMotion) {
            applyTheme();
            return;
        }

        const rect = event.currentTarget.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const radius = Math.hypot(
            Math.max(x, window.innerWidth - x),
            Math.max(y, window.innerHeight - y)
        );

        document.documentElement.style.setProperty('--theme-x', `${x}px`);
        document.documentElement.style.setProperty('--theme-y', `${y}px`);
        document.documentElement.style.setProperty(
            '--theme-radius',
            `${radius}px`
        );
        document.startViewTransition(applyTheme);
    };

    const sendQuery = async (rawQuery) => {
        const userQuery = rawQuery.trim();
        if (!userQuery || isGenerating) return;

        const sessionId = activeSessionId;
        const assistantId = newMessageId();
        const isFirstMessage =
            (activeSession?.messages || EMPTY_MESSAGES).length === 0;

        addMessage(sessionId, {
            role: 'user',
            content: userQuery,
            timestamp: now(),
        });
        addMessage(sessionId, {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: now(),
        });

        setInput('');
        setGenerating(true);
        clearAgentState(sessionId);
        stickToBottomRef.current = true;

        const controller = new AbortController();
        controllerRef.current = controller;
        const requestId = newMessageId();
        activeRequestIdRef.current = requestId;

        let watchdog = null;
        const armWatchdog = () => {
            clearTimeout(watchdog);
            watchdog = setTimeout(() => controller.abort('timeout'), 180_000);
        };
        armWatchdog();

        let streamError = null;
        let receivedDone = false;

        try {
            const events = streamQuery(
                {
                    query: userQuery,
                    request_id: requestId,
                    generate_title: isFirstMessage,
                    max_retries: 3,
                    top_k_retrieve: 15,
                    top_k_generate: 3,
                },
                { signal: controller.signal }
            );

            for await (const payload of events) {
                armWatchdog();

                switch (payload.event) {
                    case 'title':
                        applyGeneratedTitle(sessionId, payload.data || '');
                        break;

                    case 'status':
                        setLiveStatus(payload.message || '');
                        addThinkingStep(sessionId, {
                            type: 'status',
                            text: payload.message,
                        });
                        break;

                    case 'sources':
                        setSources(sessionId, payload.data || []);
                        break;

                    case 'token':
                        appendDraft(payload.data || '');
                        break;

                    case 'correction':
                        setLiveStatus(payload.message || '');
                        addThinkingStep(sessionId, {
                            type: 'fail',
                            text: payload.message,
                        });
                        setCurrentDraft('');
                        break;

                    case 'error':
                        streamError = payload.message || 'Pipeline error.';
                        break;

                    case 'done': {
                        receivedDone = true;
                        const trace = payload.trace || {};

                        if (trace.status === 'SUCCESS') {
                            updateMessage(sessionId, assistantId, {
                                content: trace.final_answer || '',
                                failed: false,
                                error: null,
                                attempts: trace.attempts ?? null,
                            });
                            setLiveStatus('Answer verified.');
                        } else if (trace.status === 'CANCELLED') {
                            updateMessage(sessionId, assistantId, {
                                failed: true,
                                error: 'Generation stopped.',
                                attempts: trace.attempts ?? null,
                            });
                        } else if (trace.status === 'ERROR') {
                            updateMessage(sessionId, assistantId, {
                                failed: true,
                                error:
                                    trace.error ||
                                    streamError ||
                                    'The pipeline failed. Please retry.',
                                attempts: trace.attempts ?? null,
                            });
                        } else {
                            updateMessage(sessionId, assistantId, {
                                failed: true,
                                error: null,
                                attempts: trace.attempts ?? null,
                            });
                            setLiveStatus('Answer could not be verified.');
                        }

                        setCurrentDraft('');
                        break;
                    }

                    default:
                        break;
                }
            }

            if (!receivedDone) {
                throw new Error(
                    'The server closed the stream before the answer completed.'
                );
            }
        } catch (error) {
            const aborted =
                error?.name === 'AbortError' || controller.signal.aborted;
            const timedOut = controller.signal.reason === 'timeout';

            updateMessage(sessionId, assistantId, {
                failed: true,
                error:
                    aborted && !timedOut ?
                        'Generation stopped.'
                    :   timedOut ?
                        'The request timed out. Please retry.'
                    :   `Connection failed: ${error.message}`,
            });
            setCurrentDraft('');
        } finally {
            clearTimeout(watchdog);
            controllerRef.current = null;
            activeRequestIdRef.current = null;
            setGenerating(false);
            setLiveStatus('');
        }
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        sendQuery(input);
    };

    return (
        <main className='flex h-dvh overflow-hidden bg-canvas text-ink'>
            <Sidebar health={health} />

            <section className='flex h-full min-w-0 flex-1 flex-col'>
                <header className='flex h-16 shrink-0 items-center gap-3 border-b border-line bg-panel/90 px-4 backdrop-blur md:px-6'>
                    <div className='flex min-w-0 flex-1 items-center gap-3'>
                        <Button
                            variant='ghost'
                            size='icon'
                            onClick={toggleLeftPanel}
                            aria-label='Show consultations'
                            className='md:hidden'>
                            <Menu aria-hidden='true' className='h-5 w-5' />
                        </Button>

                        {!leftPanelOpen && (
                            <Button
                                variant='ghost'
                                size='icon'
                                onClick={toggleLeftPanel}
                                aria-label='Show consultations'
                                className='max-md:hidden'>
                                <PanelLeft
                                    aria-hidden='true'
                                    className='h-4 w-4'
                                />
                            </Button>
                        )}

                        <div className='flex min-w-0 flex-1 items-center gap-2 md:hidden'>
                            <BrandMark />
                            <EditableTitle
                                title={
                                    activeSession?.title || 'New consultation'
                                }
                                onSave={(title) =>
                                    renameSession(activeSessionId, title)
                                }
                                className='text-[12.5px]'
                            />
                        </div>

                        <div className='hidden min-w-0 md:block'>
                            <EditableTitle
                                title={
                                    activeSession?.title || 'New consultation'
                                }
                                onSave={(title) =>
                                    renameSession(activeSessionId, title)
                                }
                                className='text-[14px]'
                            />
                        </div>
                    </div>

                    <div className='ml-auto flex items-center gap-1.5'>
                        <Button
                            variant='outline'
                            size='sm'
                            onClick={handleThemeToggle}
                            className='h-8 w-8 px-0'
                            aria-label={
                                theme === 'dark' ?
                                    'Switch to light mode'
                                :   'Switch to dark mode'
                            }
                            title={
                                theme === 'dark' ?
                                    'Switch to light mode'
                                :   'Switch to dark mode'
                            }>
                            {theme === 'dark' ?
                                <Sun
                                    aria-hidden='true'
                                    className='h-4 w-4'
                                />
                            :   <Moon
                                    aria-hidden='true'
                                    className='h-4 w-4'
                                />
                            }
                        </Button>
                        {DEMO_MODE && (
                            <Badge
                                variant='warning'
                                className='hidden sm:inline-flex'>
                                Demo
                            </Badge>
                        )}
                        <Button
                            variant='outline'
                            size='sm'
                            onClick={toggleSidePanel}
                            aria-pressed={sidePanelOpen}
                            aria-label='Evidence'
                            className='gap-2'>
                            <span className='hidden sm:inline'>Evidence</span>
                            <FileText
                                aria-hidden='true'
                                className='h-3.5 w-3.5 sm:hidden'
                            />
                            <Badge variant='navy'>{validSourceCount}</Badge>
                        </Button>
                        <Button
                            variant='outline'
                            size='sm'
                            onClick={() => clearChat(activeSessionId)}
                            disabled={isGenerating}
                            aria-label='Clear conversation'
                            title='Clear conversation'
                            className='h-8 w-8 px-0'>
                            <Trash2 aria-hidden='true' className='h-4 w-4' />
                        </Button>
                    </div>
                </header>

                <p className='sr-only' aria-live='polite'>
                    {liveStatus}
                </p>

                <div
                    ref={transcriptRef}
                    onScroll={handleScroll}
                    role='log'
                    aria-label='Conversation'
                    className='flex-1 overflow-y-auto'>
                    <div className='mx-auto flex w-full max-w-3xl flex-col gap-7 px-4 py-8 md:px-8'>
                        {messages.length === 0 ?
                            <EmptyState onAsk={sendQuery} />
                        :   null}

                        {messages.map((message, index) => {
                            const isUser = message.role === 'user';
                            const isLast = index === messages.length - 1;
                            const showDraft =
                                !isUser &&
                                isLast &&
                                isGenerating &&
                                Boolean(currentDraft);

                            if (isUser) {
                                return (
                                    <article
                                        key={message.id}
                                        className='flex justify-end'>
                                        <div className='max-w-[85%] rounded-2xl rounded-br-md bg-navy-800 px-4 py-2.5 text-white shadow-sm dark:bg-navy-600'>
                                            <p className='whitespace-pre-wrap text-[13px] leading-6'>
                                                {message.content}
                                            </p>
                                            <time className='mt-1 block text-right text-[10px] text-white/55'>
                                                {message.timestamp}
                                            </time>
                                        </div>
                                    </article>
                                );
                            }

                            return (
                                <article
                                    key={message.id}
                                    className='group flex gap-3'>
                                    <span className='mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-accent'>
                                        <Stethoscope
                                            aria-hidden='true'
                                            className='h-4 w-4'
                                        />
                                    </span>

                                    <div className='min-w-0 flex-1'>
                                        <div className='mb-1.5 flex items-center gap-2'>
                                            <span className='text-[12px] font-medium text-ink'>
                                                MedSovereign
                                            </span>
                                            <span className='text-[10px] text-faint'>
                                                {message.timestamp}
                                            </span>
                                            {message.content && (
                                                <CopyButton
                                                    text={message.content}
                                                />
                                            )}
                                        </div>

                                        {message.failed ?
                                            <FailureNotice
                                                error={message.error}
                                                attempts={message.attempts}
                                            />
                                        :   showDraft ?
                                            <div className='text-[13px] text-ink-soft'>
                                                <Markdown
                                                    content={currentDraft}
                                                />
                                                <span
                                                    aria-hidden='true'
                                                    className='ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-navy-600 align-text-bottom motion-reduce:animate-none'
                                                />
                                            </div>
                                        :   message.content ?
                                            <div className='text-[13px] text-ink-soft'>
                                                <Markdown
                                                    content={message.content}
                                                />
                                            </div>
                                        :   isGenerating ?
                                            <div className='flex items-center gap-2 text-[12.5px] text-muted'>
                                                <Spinner className='h-3.5 w-3.5 text-accent' />
                                                Searching the literature…
                                            </div>
                                        :   null}
                                    </div>
                                </article>
                            );
                        })}
                    </div>
                </div>

                <footer className='shrink-0 border-t border-line bg-panel px-3 py-3 md:px-8 md:py-4'>
                    <div className='mx-auto max-w-3xl'>
                        <form
                            onSubmit={handleSubmit}
                            className='rounded-xl border border-line bg-panel p-2 shadow-[0_1px_2px_rgba(11,37,69,0.04)] transition-shadow focus-within:border-navy-200 focus-within:ring-2 focus-within:ring-navy-100/70'>
                            <textarea
                                ref={textareaRef}
                                value={input}
                                onChange={(event) =>
                                    setInput(event.target.value)
                                }
                                onKeyDown={(event) => {
                                    if (
                                        event.key === 'Enter' &&
                                        !event.shiftKey &&
                                        !event.nativeEvent.isComposing
                                    ) {
                                        event.preventDefault();
                                        sendQuery(input);
                                    }
                                }}
                                rows={1}
                                maxLength={2000}
                                placeholder='Ask a clinical question…'
                                aria-label='Clinical question'
                                className='block max-h-40 min-h-[52px] w-full resize-none bg-transparent px-2 py-2 text-[13px] leading-6 text-ink placeholder:text-faint focus:outline-none'
                            />

                            <div className='flex items-center justify-between gap-3 px-1 pb-0.5'>
                                <div className='flex items-center gap-2 text-[10.5px] text-faint'>
                                    <span className='hidden sm:inline'>
                                        Enter to send · Shift+Enter for a new
                                        line
                                    </span>
                                    {input.length > 1700 && (
                                        <span className='tabular-nums'>
                                            {input.length}/2000
                                        </span>
                                    )}
                                </div>

                                {isGenerating ?
                                    <Button
                                        variant='danger'
                                        size='sm'
                                        onClick={handleStop}
                                        aria-label='Stop generation'
                                        className='gap-1.5'>
                                        <Square
                                            aria-hidden='true'
                                            className='h-3 w-3 fill-current'
                                        />
                                        Stop
                                    </Button>
                                :   <Button
                                        type='submit'
                                        size='sm'
                                        disabled={!input.trim()}
                                        className='gap-1.5'>
                                        <Send
                                            aria-hidden='true'
                                            className='h-3.5 w-3.5'
                                        />
                                        Send
                                    </Button>
                                }
                            </div>
                        </form>
                    </div>
                </footer>
            </section>

            <EvidencePanel />
        </main>
    );
};
