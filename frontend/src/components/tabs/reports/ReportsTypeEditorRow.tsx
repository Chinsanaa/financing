'use client';

import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { Select } from '@/components/ui/Input';
import { amountText, TYPE_CHOICES, parseTypeValue, typeChangeNote, typeValue } from './reportsHelpers';
import type { Transaction } from './reportsHelpers';

// 8 visible columns on desktop + the action column.
const COLS = 9;

export default function ReportsTypeEditorRow({
  txn,
  typeDraft,
  typeSaving,
  typeError,
  onDraftChange,
  onSave,
  onCancel,
}: {
  txn: Transaction;
  typeDraft: string;
  typeSaving: boolean;
  typeError: string;
  onDraftChange: (value: string) => void;
  onSave: (txn: Transaction) => void;
  onCancel: () => void;
}) {
  return (
    <tr className="bg-edge/[0.04]">
      <td colSpan={COLS} className="px-3 pb-4 pt-1 sm:px-4">
        <div className="ml-0 max-w-xl space-y-3 border-l-2 border-ink/70 pl-3 sm:ml-10 sm:pl-4">
          <p className="text-sm text-ink">
            What is <span className="font-medium">{txn.merchant}</span>{' '}
            <span className="num">
              ({amountText(txn)})
            </span>
            ?
          </p>
          <div className="flex flex-wrap items-end gap-2">
            <div className="w-full sm:w-[280px]">
              <Select
                aria-label="New type"
                value={typeDraft}
                onChange={(e) => onDraftChange(e.target.value)}
                className="py-2"
              >
                {TYPE_CHOICES.map((g) => (
                  <optgroup key={g.group} label={g.group}>
                    {g.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </Select>
            </div>
            <Button
              size="sm"
              onClick={() => onSave(txn)}
              loading={typeSaving}
              disabled={typeSaving || typeDraft === typeValue(txn)}
            >
              Save type
            </Button>
            <Button variant="ghost" size="sm" onClick={onCancel} disabled={typeSaving}>
              Cancel
            </Button>
          </div>
          <p className="text-[13px] text-muted">
            {typeDraft === typeValue(txn)
              ? 'Pick a different type. The amount never changes.'
              : `${typeChangeNote(parseTypeValue(typeDraft).kind)} The amount never changes.`}
          </p>
          {typeError && <Alert kind="error">{typeError}</Alert>}
        </div>
      </td>
    </tr>
  );
}
