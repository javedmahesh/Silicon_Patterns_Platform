import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { ChevronDown, Search } from "lucide-react";

import { cx } from "@/lib/cx";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cx(
          "h-8 w-full rounded-md border border-line bg-control px-2.5 text-13 text-fg",
          "placeholder:text-fg-subtle focus:border-accent focus:outline-none",
          className,
        )}
        {...props}
      />
    );
  },
);

/** Input with a leading search icon. */
export const SearchInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function SearchInput({ className, ...props }, ref) {
    return (
      <div className="relative">
        <Search
          size={14}
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-subtle"
        />
        <input
          ref={ref}
          className={cx(
            "h-8 w-full rounded-md border border-line bg-control pl-8 pr-2.5 text-13 text-fg",
            "placeholder:text-fg-subtle focus:border-accent focus:outline-none",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  children: ReactNode;
}

export function Select({ className, children, ...props }: SelectProps) {
  return (
    <div className="relative inline-flex">
      <select
        className={cx(
          "h-8 appearance-none rounded-md border border-line bg-control pl-2.5 pr-7 text-13 text-fg",
          "focus:border-accent focus:outline-none",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-fg-subtle"
      />
    </div>
  );
}
