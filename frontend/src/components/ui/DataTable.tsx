import { ChevronDown, ChevronUp, Search } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { Button } from "./Button";
import { Input } from "./Field";
import { EmptyState } from "./State";

export interface Column<T> {
  key: string;
  header: string;
  value: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  className?: string;
}

export function DataTable<T>({
  rows,
  columns,
  getRowId,
  onRowClick,
  emptyTitle = "No records",
  initialPageSize = 15,
}: {
  rows: T[];
  columns: Column<T>[];
  getRowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  initialPageSize?: number;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState(columns[0]?.key ?? "");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const next = normalized
      ? rows.filter((row) => JSON.stringify(row).toLowerCase().includes(normalized))
      : rows;
    const column = columns.find((item) => item.key === sortKey);
    const sorted = [...next].sort((a, b) => {
      const av = column?.sortValue?.(a) ?? String(column?.value(a) ?? "");
      const bv = column?.sortValue?.(b) ?? String(column?.value(b) ?? "");
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return sorted;
  }, [columns, query, rows, sortDir, sortKey]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(safePage * pageSize, safePage * pageSize + pageSize);

  function toggleSort(key: string) {
    setPage(0);
    if (sortKey === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  if (!rows.length) {
    return <EmptyState title={emptyTitle} detail="Generate or audit a world to populate this view." />;
  }

  return (
    <div className="rounded-lg border border-line bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-3">
        <label className="relative min-w-64 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            className="pl-9"
            placeholder="Search records"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(0);
            }}
          />
        </label>
        <div className="flex items-center gap-2 text-sm text-muted">
          <span>{filtered.length} records</span>
          <select
            className="min-h-9 rounded-lg border border-line bg-white px-2 text-sm"
            value={pageSize}
            onChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(0);
            }}
          >
            {[10, 15, 25, 50].map((size) => (
              <option key={size} value={size}>
                {size} / page
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] border-collapse text-sm">
          <thead>
            <tr className="bg-slate-100 text-left text-xs font-bold uppercase text-muted">
              {columns.map((column) => (
                <th key={column.key} className="border-b border-line px-3 py-2">
                  <button className="flex items-center gap-1" onClick={() => toggleSort(column.key)}>
                    {column.header}
                    {sortKey === column.key ? sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" /> : null}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={getRowId(row)}
                className="cursor-pointer border-b border-line last:border-b-0 hover:bg-slate-50"
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column) => (
                  <td key={column.key} className={`max-w-72 truncate px-3 py-2 ${column.className ?? ""}`}>
                    {column.value(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-line p-3 text-sm text-muted">
        <span>
          Page {safePage + 1} of {pageCount}
        </span>
        <div className="flex gap-2">
          <Button disabled={safePage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>
            Previous
          </Button>
          <Button disabled={safePage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
