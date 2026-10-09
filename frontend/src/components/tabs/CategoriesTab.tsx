'use client';

import { useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { Tags, Trash2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui-feedback';
import Button from '@/components/ui/Button';
import { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import CategoryColorPicker from '@/components/ui/CategoryColorPicker';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { hashCategoryKey, toneForKey } from '@/utils/categoryColors';
import { FIELD_CLASSES } from '@/components/ui/Input';

interface Category {
  id: string;
  name: string;
  is_catch_all?: boolean;
  color?: string | null;
}

export default function CategoriesTab() {
  const { data, setData, loading, error: loadError } = useApi<{ categories: Category[] }>('/categories/');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [savingColorId, setSavingColorId] = useState<string | null>(null);

  const categories = data?.categories || [];

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCategoryName.trim()) return;

    try {
      setError('');
      setMessage('');
      const res = await api.categories.create(newCategoryName.trim());
      setData((prev) =>
        prev ? { ...prev, categories: [...prev.categories, res.data.category] } : prev
      );
      setNewCategoryName('');
      setMessage('Category added!');
      invalidate('/categories');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add category');
    }
  };

  const handleDeleteCategory = async (id: string) => {
    if (!confirm('Delete this category? Its transactions will be reassigned to your catch-all category.')) return;

    try {
      setError('');
      await api.categories.delete(id);
      setData((prev) =>
        prev ? { ...prev, categories: prev.categories.filter((c) => c.id !== id) } : prev
      );
      setMessage('Category deleted');
      invalidate('/categories');
      invalidate('/dashboard'); // reassignment changes breakdowns
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete category');
    }
  };

  const handleColorChange = async (cat: Category, colorKey: string | null) => {
    const previous = cat.color ?? null;
    if (colorKey === previous) return;

    setError('');
    setSavingColorId(cat.id);
    // Optimistic: recolor immediately; revert on failure.
    setData((prev) =>
      prev
        ? {
            ...prev,
            categories: prev.categories.map((c) =>
              c.id === cat.id ? { ...c, color: colorKey } : c
            ),
          }
        : prev
    );
    try {
      await api.categories.update(cat.id, { color: colorKey });
      // Recolors badges/charts everywhere useCategoryColors is consumed.
      invalidate('/categories');
    } catch (err: any) {
      setData((prev) =>
        prev
          ? {
              ...prev,
              categories: prev.categories.map((c) =>
                c.id === cat.id ? { ...c, color: previous } : c
              ),
            }
          : prev
      );
      setError(err.response?.data?.detail || 'Failed to save color');
    } finally {
      setSavingColorId(null);
    }
  };

  return (
    <div className="w-full space-y-6" data-tour-id="categories-list">
      <SectionHeader
        title="Categories"
        description="The labels your model learns to predict — keep them broad enough to be learnable. Each color follows its category everywhere: charts, badges and reports."
      />

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      <form onSubmit={handleAddCategory} className="flex max-w-xl gap-2">
        <input
          type="text"
          value={newCategoryName}
          onChange={(e) => setNewCategoryName(e.target.value)}
          placeholder="New category name"
          aria-label="New category name"
          className={`${FIELD_CLASSES} flex-1`}
        />
        <Button type="submit" variant="outline">Add category</Button>
      </form>

      {loading ? (
        <SkeletonRows rows={6} />
      ) : categories.length === 0 ? (
        <EmptyState
          icon={Tags}
          title="No categories yet"
          description="Add a few categories to start labeling — Food, Transport and Shopping are good openers."
        />
      ) : (
        // A ruled list: swatch + name, then the color choice and delete.
        // No transforms/overflow on rows — they would trap the picker popover.
        <ul className="grid border-t border-ink/80 sm:grid-cols-2 sm:gap-x-12 2xl:grid-cols-3">
          <AnimatePresence initial={false}>
            {categories.map((cat) => {
              // Colors chosen by OTHER categories are disabled in the picker.
              const takenBy = new Map<string, string>();
              for (const other of categories) {
                if (other.id !== cat.id && other.color) takenBy.set(other.color, other.name);
              }
              return (
                <m.li
                  key={cat.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.12 } }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center gap-3 border-b border-edge/12 py-3"
                >
                  <span className="flex min-w-0 flex-1 items-center gap-2">
                    <Badge tone={toneForKey(cat.color || hashCategoryKey(cat.name))}>{cat.name}</Badge>
                    {cat.is_catch_all && <Badge tone="neutral">catch-all</Badge>}
                  </span>
                  <CategoryColorPicker
                    categoryName={cat.name}
                    color={cat.color}
                    takenBy={takenBy}
                    saving={savingColorId === cat.id}
                    onSelect={(key) => handleColorChange(cat, key)}
                  />
                  {cat.is_catch_all ? (
                    <span className="w-8" aria-hidden="true" />
                  ) : (
                    <button
                      onClick={() => handleDeleteCategory(cat.id)}
                      aria-label={`Delete ${cat.name}`}
                      className="rounded-md p-2 text-muted transition-colors hover:bg-danger/8 hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </m.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}
