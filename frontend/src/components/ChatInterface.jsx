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
import { streamQuery } from '../lib/api';
import { LeftPanel, SidePanel } from './AgentUI';
import { Markdown } from './Markdown';

const newMessageId = () =>
    typeof crypto !== 'undefined' && crypto.randomUUID ?
        crypto.randomUUID()
    :   String(Date.now());

const EMPTY_MESSAGES = [];

const now = () =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const FailureNotice = ({ error, attempts }) => (
    <div
        role='alert'
        className='flex items-start space-x-2 text-xs font-semibold text-punch-red-300 md:text-sm'>
        <AlertCircle
            aria-hidden='true'
            className='mt-0.5 h-4 w-4 shrink-0 text-punch-red-400'
        />
        <span>
            {error ||
                `Could not verify this answer against the corpus after ${
                    attempts ?? 'the maximum number of'
                } attempt(s).`}
        </span>
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
    } = useChatStore();

    const [input, setInput] = useState('');
    const [liveStatus, setLiveStatus] = useState('');
    const controllerRef = useRef(null);
    const transcriptRef = useRef(null);
    const stickToBottomRef = useRef(true);

    const activeSession =
        sessions.find((session) => session.id === activeSessionId) ||
        sessions[0];
    const messages = activeSession?.messages || EMPTY_MESSAGES;

    useEffect(() => {
        const transcript = transcriptRef.current;
        if (transcript && stickToBottomRef.current) {
            transcript.scrollTop = transcript.scrollHeight;
        }
    }, [messages, currentDraft]);

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
    };

    const handleSend = async (event) => {
        event.preventDefault();
        const userQuery = input.trim();

        if (!userQuery || isGenerating) return;

        const sessionId = activeSessionId;
        const assistantId = newMessageId();

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

        let watchdog = null;
        const armWatchdog = () => {
            clearTimeout(watchdog);
            watchdog = setTimeout(
                () => controller.abort('timeout'),
                180_000
            );
        };
        armWatchdog();

        let streamError = null;
        let receivedDone = false;

        try {
            const events = streamQuery(
                {
                    query: userQuery,
                    max_retries: 3,
                    top_k_retrieve: 15,
                    top_k_generate: 3,
                },
                { signal: controller.signal }
            );

            for await (const payload of events) {
                armWatchdog();

                switch (payload.event) {
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
                error: aborted && !timedOut ?
                    'Generation stopped.' :
                    timedOut ?
                        'The request timed out. Please retry.'
                    :   `Connection failed: ${error.message}`,
            });
            setCurrentDraft('');
        } finally {
            clearTimeout(watchdog);
            controllerRef.current = null;
            setGenerating(false);
            setLiveStatus('');
        }
    };

    return (
        <main className='flex h-dvh overflow-hidden bg-space-indigo-900'>
            <LeftPanel />

            <section className='flex h-full min-w-0 flex-1 flex-col'>
                <header className='flex shrink-0 items-center justify-between border-b border-[#162236] bg-space-indigo-950 px-4 py-3 md:px-6 md:py-4'>
                    <section className='flex items-center space-x-3'>
                        <button
                            type='button'
                            onClick={toggleLeftPanel}
                            aria-label={
                                leftPanelOpen ?
                                    'Hide history panel'
                                :   'Show history panel'
                            }
                            aria-expanded={leftPanelOpen}
                            className='cursor-pointer text-platinum-100 transition-colors hover:text-platinum-200'>
                            {leftPanelOpen ?
                                <PanelLeftClose
                                    aria-hidden='true'
                                    className='h-4 w-4 text-punch-red-500'
                                />
                            :   <PanelLeftOpen
                                    aria-hidden='true'
                                    className='h-4 w-4'
                                />
                            }
                        </button>
                        <Activity
                            aria-hidden='true'
                            className='h-5 w-5 text-punch-red-500'
                        />
                        <h1 className='text-sm font-bold tracking-wider text-platinum-100'>
                            Medical Sovereign RAG
                        </h1>
                    </section>

                    <section className='flex items-center space-x-3'>
                        <button
                            type='button'
                            onClick={() => clearChat(activeSessionId)}
                            disabled={isGenerating}
                            aria-label='Clear session messages'
                            className='cursor-pointer text-platinum-100 transition-colors hover:text-punch-red-500 disabled:cursor-not-allowed disabled:opacity-30'>
                            <Trash2 aria-hidden='true' className='h-4 w-4' />
                        </button>
                        <button
                            type='button'
                            onClick={toggleSidePanel}
                            aria-label={
                                sidePanelOpen ?
                                    'Hide reasoning panel'
                                :   'Show reasoning panel'
                            }
                            aria-expanded={sidePanelOpen}
                            className='cursor-pointer text-platinum-100 transition-colors hover:text-platinum-200'>
                            {sidePanelOpen ?
                                <PanelRightClose
                                    aria-hidden='true'
                                    className='h-4 w-4 text-punch-red-400'
                                />
                            :   <PanelRightOpen
                                    aria-hidden='true'
                                    className='h-4 w-4'
                                />
                            }
                        </button>
                    </section>
                </header>

                <p className='sr-only' aria-live='polite'>
                    {liveStatus}
                </p>

                <div
                    ref={transcriptRef}
                    onScroll={handleScroll}
                    role='log'
                    aria-label='Conversation transcript'
                    className='flex-1 space-y-4 overflow-y-auto bg-space-indigo-900 p-4 md:px-12'>
                    {messages.length === 0 && (
                        <div className='mx-auto mt-10 max-w-xl rounded border border-[#162236] bg-space-indigo-950/60 p-5 text-center'>
                            <p className='text-sm font-semibold text-platinum-100'>
                                Ask a clinical question
                            </p>
                            <p className='mt-2 text-xs leading-relaxed text-platinum-300 md:text-sm'>
                                Answers are grounded in the retrieved corpus.
                                Try “What are the symptoms and treatments
                                for acute bronchitis?”
                            </p>
                        </div>
                    )}

                    {messages.map((message, index) => {
                        const isUser = message.role === 'user';
                        const isLast = index === messages.length - 1;
                        const showDraft =
                            !isUser &&
                            isLast &&
                            isGenerating &&
                            Boolean(currentDraft);

                        return (
                            <article
                                key={message.id}
                                className={`flex flex-col ${
                                    isUser ? 'items-end' : 'items-start'
                                }`}>
                                <div
                                    className={`max-w-xl rounded-md px-4 py-3 text-xs text-platinum-100 md:max-w-2xl md:text-sm ${
                                        isUser ?
                                            'bg-space-indigo-950'
                                        :   'bg-space-indigo-800'
                                    }`}>
                                    {!isUser && message.failed ?
                                        <FailureNotice
                                            error={message.error}
                                            attempts={message.attempts}
                                        />
                                    :   isUser ?
                                        <p className='whitespace-pre-wrap leading-relaxed'>
                                            {message.content}
                                        </p>
                                    :   <>
                                            {showDraft ?
                                                <div className='text-platinum-200'>
                                                    <Markdown
                                                        content={currentDraft}
                                                    />
                                                    <span
                                                        aria-hidden='true'
                                                        className='ml-1 inline-block h-3 w-1.5 animate-pulse bg-punch-red-500 align-middle motion-reduce:animate-none'
                                                    />
                                                </div>
                                            :   message.content ?
                                                <Markdown
                                                    content={message.content}
                                                />
                                            :   isGenerating ?
                                                <p className='text-platinum-300 italic'>
                                                    Retrieving evidence…
                                                </p>
                                            :   null
                                            }
                                        </>
                                    }

                                    <time className='mt-1.5 block text-right font-mono text-[10px] text-platinum-400'>
                                        {message.timestamp}
                                    </time>
                                </div>
                            </article>
                        );
                    })}
                </div>

                <footer className='shrink-0 bg-space-indigo-950 p-3 md:p-4'>
                    <form
                        onSubmit={handleSend}
                        className='relative mx-auto flex max-w-4xl items-end rounded-md bg-space-indigo-900'>
                        <textarea
                            value={input}
                            onChange={(event) => setInput(event.target.value)}
                            onKeyDown={(event) => {
                                if (
                                    event.key === 'Enter' &&
                                    !event.shiftKey &&
                                    !event.nativeEvent.isComposing
                                ) {
                                    event.preventDefault();
                                    handleSend(event);
                                }
                            }}
                            rows={2}
                            maxLength={2000}
                            placeholder='Enter clinical query…'
                            aria-label='Clinical query'
                            className='w-full resize-none bg-transparent py-3 pr-28 pl-4 text-xs text-platinum-100 placeholder:text-platinum-400 focus:outline-none md:text-sm'
                        />

                        {isGenerating ?
                            <button
                                type='button'
                                onClick={handleStop}
                                aria-label='Stop generation'
                                className='absolute right-2 bottom-2 flex cursor-pointer items-center space-x-1 rounded bg-punch-red-700 px-3 py-2 text-platinum-100 transition-colors hover:bg-punch-red-600'>
                                <Square
                                    aria-hidden='true'
                                    className='size-3 fill-current'
                                />
                                <span className='text-xs font-bold'>Stop</span>
                            </button>
                        :   <button
                                type='submit'
                                disabled={!input.trim()}
                                className='absolute right-2 bottom-2 flex cursor-pointer items-center space-x-1 rounded bg-blue-950 px-3 py-2 text-platinum-100 transition-colors hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-30'>
                                <span className='text-xs font-bold'>Send</span>
                                <Send
                                    aria-hidden='true'
                                    className='size-3'
                                />
                            </button>
                        }
                    </form>

                    <p className='mx-auto mt-2 max-w-4xl text-center text-[10px] text-platinum-400'>
                        Retrieval-grounded. Not a medical device and not
                        validated for clinical use.
                    </p>
                </footer>
            </section>

            <SidePanel />
        </main>
    );
};
