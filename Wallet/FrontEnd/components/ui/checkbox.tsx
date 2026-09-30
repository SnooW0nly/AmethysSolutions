'use client'

import * as React from 'react'
import * as CheckboxPrimitive from '@radix-ui/react-checkbox'
import { CheckIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

interface CheckboxProps extends React.ComponentProps<typeof CheckboxPrimitive.Root> {
  label?: React.ReactNode
  description?: React.ReactNode
  className?: string
  labelClassName?: string
}

function Checkbox({
  className,
  label,
  description,
  labelClassName,
  id,
  ...props
}: CheckboxProps) {
  const checkboxId = id || React.useId()
  
  return (
    <div className={cn('flex items-start gap-3', className)}>
    <CheckboxPrimitive.Root
        id={checkboxId}
      data-slot="checkbox"
      className={cn(
          'mt-0.5 shrink-0 size-4 rounded border border-foreground/20 bg-foreground/5',
          'data-[state=checked]:bg-primary data-[state=checked]:border-primary',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-0',
          'transition-colors cursor-pointer',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'hover:border-foreground/40 data-[state=checked]:hover:bg-primary/90',
          className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
          className="flex items-center justify-center text-primary-foreground"
      >
        <CheckIcon className="size-3.5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
      {(label || description) && (
        <label
          htmlFor={checkboxId}
          className={cn('flex-1 cursor-pointer', labelClassName)}
        >
          {label && (
            <div className="text-sm font-medium text-foreground">
              {label}
            </div>
          )}
          {description && (
            <div className="text-xs text-foreground/60 mt-1">
              {description}
            </div>
          )}
        </label>
      )}
    </div>
  )
}

export { Checkbox }
