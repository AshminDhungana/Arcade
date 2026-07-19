import { useState, useRef, useEffect } from 'react';
import { useMembers } from '@/api/members';
import { Search, User } from 'lucide-react';
import type { Member } from '@/types/members';

export function MemberSearch({
  onSelect,
  placeholder = 'Search members by name or phone…',
}: {
  onSelect: (m: Member) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState('');
  const [debounced, setDebounced] = useState('');
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 280);
    return () => clearTimeout(t);
  }, [q]);

  const { data: results = [], isFetching } = useMembers(debounced);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  return (
    <div ref={boxRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          placeholder={placeholder}
          className="w-full rounded-lg border border-input bg-popover py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus-visible:ring-ring focus-visible:border-ring focus-visible:outline-none"
        />
      </div>
      {open && debounced && (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-border bg-popover shadow-xl">
          {results.length === 0 && !isFetching && (
            <li className="px-3 py-2 text-sm text-muted-foreground">No members found</li>
          )}
          {results.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(m);
                  setOpen(false);
                  setQ(m.name);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground hover:bg-secondary"
              >
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{m.name}</span>
                <span className="ml-auto tabular-nums text-muted-foreground">{m.phone}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
