/**
 * Minimal className joiner. The shadcn/ui reference components this project
 * ports from expect a `cn()` from "@/lib/utils" (usually clsx + tailwind-merge);
 * we don't need Tailwind class-conflict resolution here, so a plain filter+join
 * avoids adding two more dependencies for it.
 */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
