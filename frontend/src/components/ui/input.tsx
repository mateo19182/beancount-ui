import * as React from 'react'
import { cn } from '@/lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'flex h-9 w-full rounded-md border border-gray-300 bg-transparent px-3 py-1 text-sm dark:border-gray-700',
        className
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'
