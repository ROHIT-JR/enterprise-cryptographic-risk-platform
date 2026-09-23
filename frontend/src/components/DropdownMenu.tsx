import * as RadixDropdown from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../utils/cn";

/**
 * Thin themed wrapper around @radix-ui/react-dropdown-menu — the same
 * primitive shadcn/ui's own DropdownMenu wraps (https://ui.shadcn.com/docs/components/dropdown-menu).
 * Gives the checkmark-on-selected-item + smooth open/close behavior
 * verified live on the reference demo, replacing raw <select> filters.
 */

export const DropdownMenu = RadixDropdown.Root;
export const DropdownMenuTrigger = RadixDropdown.Trigger;

export function DropdownMenuContent({ children, className, ...props }: RadixDropdown.DropdownMenuContentProps) {
  return (
    <RadixDropdown.Portal>
      <RadixDropdown.Content
        sideOffset={6}
        align="start"
        className={cn(
          "z-50 min-w-[10rem] overflow-hidden rounded-lg border p-1 shadow-popover",
          "data-[state=open]:animate-[fadeIn_150ms_ease-out] data-[state=closed]:animate-[fadeIn_100ms_ease-in_reverse]",
          className,
        )}
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
        {...props}
      >
        {children}
      </RadixDropdown.Content>
    </RadixDropdown.Portal>
  );
}

export function DropdownMenuItem({
  children,
  selected,
  className,
  ...props
}: RadixDropdown.DropdownMenuItemProps & { selected?: boolean }) {
  return (
    <RadixDropdown.Item
      className={cn(
        "interactive flex cursor-pointer items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs outline-none",
        "data-[highlighted]:bg-[var(--bg-hover)]",
        className,
      )}
      style={{ color: "var(--text-secondary)" }}
      {...props}
    >
      <span>{children}</span>
      {selected && <Check className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--accent)" }} />}
    </RadixDropdown.Item>
  );
}

/** Ready-made trigger button styled like `.field`, with a chevron that rotates when open. */
export function DropdownMenuFieldTrigger({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <DropdownMenuTrigger asChild>
      <button type="button" className={cn("field interactive flex items-center justify-between gap-2 text-left", className)}>
        <span className="truncate">{children}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform data-[state=open]:rotate-180" style={{ color: "var(--text-muted)" }} />
      </button>
    </DropdownMenuTrigger>
  );
}
