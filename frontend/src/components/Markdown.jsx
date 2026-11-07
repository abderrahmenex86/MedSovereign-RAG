import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components = {
    p: ({ children }) => (
        <p className='mb-3 leading-7 last:mb-0'>{children}</p>
    ),
    ul: ({ children }) => (
        <ul className='mb-3 list-disc space-y-1.5 pl-5'>{children}</ul>
    ),
    ol: ({ children }) => (
        <ol className='mb-3 list-decimal space-y-1.5 pl-5'>{children}</ol>
    ),
    li: ({ children }) => <li className='leading-7'>{children}</li>,
    h1: ({ children }) => (
        <h1 className='mt-4 mb-2 text-[17px] font-semibold text-ink first:mt-0'>
            {children}
        </h1>
    ),
    h2: ({ children }) => (
        <h2 className='mt-4 mb-2 text-[15px] font-semibold text-ink first:mt-0'>
            {children}
        </h2>
    ),
    h3: ({ children }) => (
        <h3 className='mt-3 mb-1.5 text-[14px] font-semibold text-ink first:mt-0'>
            {children}
        </h3>
    ),
    h4: ({ children }) => (
        <h4 className='mt-3 mb-1.5 text-[13px] font-semibold text-ink first:mt-0'>
            {children}
        </h4>
    ),
    strong: ({ children }) => (
        <strong className='font-semibold text-ink'>{children}</strong>
    ),
    em: ({ children }) => <em className='italic'>{children}</em>,
    a: ({ href, children }) => (
        <a
            href={href}
            target='_blank'
            rel='noreferrer noopener'
            className='font-medium text-accent underline decoration-navy-200 underline-offset-4 hover:text-ink'>
            {children}
        </a>
    ),
    code: ({ className, children }) =>
        className?.startsWith('language-') ?
            <code className='font-mono text-[0.85em]'>{children}</code>
        :   <code className='rounded-md bg-surface px-1.5 py-0.5 font-mono text-[0.85em] text-ink ring-1 ring-line'>
                {children}
            </code>,
    pre: ({ children }) => (
        <pre className='mb-3 overflow-x-auto rounded-lg bg-navy-800 p-3 text-[12px] leading-6 text-white/90 dark:bg-surface-strong dark:text-ink'>
            {children}
        </pre>
    ),
    blockquote: ({ children }) => (
        <blockquote className='mb-3 border-l-2 border-navy-200 pl-3 text-muted italic'>
            {children}
        </blockquote>
    ),
    hr: () => <hr className='my-4 border-line' />,
    table: ({ children }) => (
        <div className='mb-3 overflow-x-auto'>
            <table className='w-full border-collapse text-left text-[12.5px]'>
                {children}
            </table>
        </div>
    ),
    th: ({ children }) => (
        <th className='border-b border-line px-2 py-1.5 font-medium text-ink'>
            {children}
        </th>
    ),
    td: ({ children }) => (
        <td className='border-b border-line/70 px-2 py-1.5 align-top'>
            {children}
        </td>
    ),
};

export const Markdown = memo(function Markdown({ content }) {
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            skipHtml
            components={components}>
            {content}
        </ReactMarkdown>
    );
});
