import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components = {
    p: ({ children }) => <p className='mb-2 leading-relaxed last:mb-0'>{children}</p>,
    ul: ({ children }) => (
        <ul className='mb-2 list-disc space-y-1 pl-5'>{children}</ul>
    ),
    ol: ({ children }) => (
        <ol className='mb-2 list-decimal space-y-1 pl-5'>{children}</ol>
    ),
    li: ({ children }) => <li className='leading-relaxed'>{children}</li>,
    h1: ({ children }) => (
        <h1 className='mt-3 mb-2 text-base font-bold text-platinum-50'>
            {children}
        </h1>
    ),
    h2: ({ children }) => (
        <h2 className='mt-3 mb-2 text-sm font-bold text-platinum-50'>
            {children}
        </h2>
    ),
    h3: ({ children }) => (
        <h3 className='mt-2 mb-1 text-sm font-semibold text-platinum-50'>
            {children}
        </h3>
    ),
    h4: ({ children }) => (
        <h4 className='mt-2 mb-1 text-xs font-semibold uppercase tracking-wide text-platinum-200'>
            {children}
        </h4>
    ),
    strong: ({ children }) => (
        <strong className='font-semibold text-platinum-50'>{children}</strong>
    ),
    em: ({ children }) => <em className='italic'>{children}</em>,
    a: ({ href, children }) => (
        <a
            href={href}
            target='_blank'
            rel='noreferrer noopener'
            className='text-punch-red-300 underline decoration-punch-red-500/60 underline-offset-2 hover:text-punch-red-200'>
            {children}
        </a>
    ),
    code: ({ className, children }) =>
        className?.startsWith('language-') ?
            <code className='font-mono text-[0.85em]'>{children}</code>
        :   <code className='rounded bg-space-indigo-950 px-1 py-0.5 font-mono text-[0.85em] text-platinum-200'>
                {children}
            </code>,
    pre: ({ children }) => (
        <pre className='mb-2 overflow-x-auto rounded border border-[#162236] bg-space-indigo-950 p-3'>
            {children}
        </pre>
    ),
    blockquote: ({ children }) => (
        <blockquote className='mb-2 border-l-2 border-punch-red-500/60 pl-3 text-platinum-200 italic'>
            {children}
        </blockquote>
    ),
    hr: () => <hr className='my-3 border-[#162236]' />,
    table: ({ children }) => (
        <div className='mb-2 overflow-x-auto'>
            <table className='w-full border-collapse text-left text-[0.85em]'>
                {children}
            </table>
        </div>
    ),
    th: ({ children }) => (
        <th className='border border-[#1e2c47] px-2 py-1 font-semibold text-platinum-100'>
            {children}
        </th>
    ),
    td: ({ children }) => (
        <td className='border border-[#1e2c47] px-2 py-1 align-top'>
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
