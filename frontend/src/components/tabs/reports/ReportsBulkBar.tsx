'use client';

import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { Select } from '@/components/ui/Input';
import type { Category } from '@/types/v5';

export default function ReportsBulkBar({
  selectedCount,
  bulkCategoryId,
  onBulkCategoryChange,
  categories,
  onApply,
  applying,
  onClear,
  error,
}: {
  selectedCount: number;
  bulkCategoryId: string;
  onBulkCategoryChange: (id: string) => void;
  categories: Category[];
  onApply: () => void;
  applying: boolean;
  onClear: () => void;
  error: string;
}) {
  return (
    <Card className="flex flex-wrap items-center gap-3 border-accent/25 p-4">
      <p className="text-sm font-medium">{selectedCount} selected</p>
      <div className="w-[200px]">
        <Select value={bulkCategoryId} onChange={(e) => onBulkCategoryChange(e.target.value)}>
          <option value="" disabled>
            Move to category…
          </option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>
      <Button size="sm" onClick={onApply} loading={applying} disabled={!bulkCategoryId}>
        Apply
      </Button>
      <Button variant="ghost" size="sm" onClick={onClear}>
        Clear selection
      </Button>
    {error && <Alert kind="error">{error}</Alert>}
  </Card>
  );
}
