import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

const buttonVariants = {
    primary:
        'bg-navy-800 text-white hover:bg-navy-700 active:bg-navy-900 shadow-sm dark:bg-navy-600 dark:hover:bg-navy-500 dark:active:bg-navy-700',
    secondary: 'bg-navy-50 text-ink hover:bg-navy-100',
    outline:
        'border border-line bg-panel text-ink-soft hover:border-navy-200 hover:bg-navy-50 hover:text-ink',
    ghost: 'text-muted hover:bg-surface hover:text-ink',
    danger:
        'border border-danger/25 bg-panel text-danger hover:bg-danger-soft',
};

const buttonSizes = {
    sm: 'h-8 gap-1.5 px-2.5 text-xs',
    md: 'h-9 gap-2 px-3.5 text-[13px]',
    icon: 'h-9 w-9',
};

export const Button = forwardRef(function Button(
    {
        variant = 'primary',
        size = 'md',
        type = 'button',
        className,
        ...props
    },
    ref
) {
    return (
        <button
            ref={ref}
            type={type}
            className={cn(
                'inline-flex shrink-0 items-center justify-center rounded-lg font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-40',
                buttonVariants[variant],
                buttonSizes[size],
                className
            )}
            {...props}
        />
    );
});

export const Badge = ({ variant = 'muted', className, children }) => {
    const variants = {
        navy: 'bg-navy-50 text-accent ring-navy-100',
        muted: 'bg-surface text-muted ring-line',
        success: 'bg-success-soft text-success ring-success/15',
        warning: 'bg-warning-soft text-warning ring-warning/15',
        danger: 'bg-danger-soft text-danger ring-danger/15',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset',
                variants[variant],
                className
            )}>
            {children}
        </span>
    );
};

export const Tabs = ({ items, value, onChange, className }) => (
    <div
        role='tablist'
        aria-label='Evidence views'
        className={cn(
            'inline-flex items-center gap-1 rounded-lg bg-surface p-1 ring-1 ring-line/70',
            className
        )}>
        {items.map((item) => {
            const active = item.value === value;

            return (
                <button
                    key={item.value}
                    type='button'
                    role='tab'
                    aria-selected={active}
                    onClick={() => onChange(item.value)}
                    className={cn(
                        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11.5px] font-medium transition-colors',
                        active ?
                            'bg-panel text-ink shadow-sm ring-1 ring-line'
                        :   'text-muted hover:text-ink'
                    )}>
                    {item.label}
                    {item.count != null && (
                        <span
                            className={cn(
                                'inline-flex min-w-4 items-center justify-center rounded px-1 text-[10px]',
                                active ?
                                    'bg-navy-50 text-accent'
                                :   'bg-panel/70 text-muted'
                            )}>
                            {item.count}
                        </span>
                    )}
                </button>
            );
        })}
    </div>
);

export const Spinner = ({ className }) => (
    <Loader2
        aria-hidden='true'
        className={cn('h-4 w-4 animate-spin', className)}
    />
);
