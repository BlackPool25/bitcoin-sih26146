import * as React from "react";
import { cn } from "@/lib/utils";

export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>): React.JSX.Element {
  return (
    <div className="relative w-full overflow-auto">
      <table data-slot="table" className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>): React.JSX.Element {
  return <thead data-slot="table-header" className={cn("[&_tr]:border-b", className)} {...props} />;
}

export function TableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>): React.JSX.Element {
  return <tbody data-slot="table-body" className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}

export function TableFooter({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>): React.JSX.Element {
  return <tfoot data-slot="table-footer" className={cn("bg-muted font-medium [&>tr]:last:border-b-0", className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>): React.JSX.Element {
  return <tr data-slot="table-row" className={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", className)} {...props} />;
}

export function TableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>): React.JSX.Element {
  return <th data-slot="table-head" className={cn("h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0", className)} {...props} />;
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>): React.JSX.Element {
  return <td data-slot="table-cell" className={cn("p-2 align-middle [&:has([role=checkbox])]:pr-0", className)} {...props} />;
}

export function TableCaption({ className, ...props }: React.HTMLAttributes<HTMLTableCaptionElement>): React.JSX.Element {
  return <caption data-slot="table-caption" className={cn("mt-4 text-sm text-muted-foreground", className)} {...props} />;
}
