import { api } from './api';

/** Save a Blob as a file via a temporary object URL. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Download every transaction as .xlsx (server-built, filename from the
 *  Content-Disposition header). Throws on failure so callers can show it. */
export async function downloadTransactionsXlsx(): Promise<void> {
  const response = await api.export.xlsx();
  const filename =
    response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') ||
    'transactions.xlsx';
  downloadBlob(response.data, filename);
}
