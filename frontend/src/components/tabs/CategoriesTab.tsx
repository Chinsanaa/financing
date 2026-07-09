'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Tags, Trash2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import CategoryColorPicker from '@/components/ui/CategoryColorPicker';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';
import { hashCategoryKey, toneForKey } from '@/utils/categoryColors';

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
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <SectionHeader label="Model" title="Categories" />
      <p className="-mt-4 text-sm text-muted">
        The labels your model learns to predict. Keep them broad enough to be learnable.
        Pick a color per category — it's used everywhere: charts, badges, and reports.
      </p>

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      <Card className="p-4">
        <form onSubmit={handleAddCategory} className="flex gap-2">
          <input
            type="text"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            placeholder="New category name"
            className="flex-1 rounded-lg border border-edge/10 bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-muted outline-none transition-colors focus:border-accent/60 focus:ring-2 focus:ring-accent/20"
          />
          <Button type="submit">Add</Button>
        </form>
      </Card>

      {loading ? (
        <SkeletonRows rows={6} />
      ) : categories.length === 0 ? (
        <EmptyState
          icon={Tags}
          title="No categories yet"
          description="Add a few categories to start labeling — Food, Transport and Shopping are good openers."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence initial={false}>
            {categories.map((cat) => {
              // Colors chosen by OTHER categories are disabled in the picker.
              const takenBy = new Map<string, string>();
              for (const other of categories) {
                if (other.id !== cat.id && other.color) takenBy.set(other.color, other.name);
              }
              return (
                <motion.div
                  key={cat.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -24 }}
                  transition={{ duration: 0.2 }}
                >
                  <Card className="flex h-full flex-col justify-between gap-3 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={toneForKey(cat.color || hashCategoryKey(cat.name))}>
                        {cat.name}
                      </Badge>
                      {cat.is_catch_all && <Badge tone="neutral">catch-all</Badge>}
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <CategoryColorPicker
                        categoryName={cat.name}
                        color={cat.color}
                        takenBy={takenBy}
                        saving={savingColorId === cat.id}
                        onSelect={(key) => handleColorChange(cat, key)}
                      />
                      {!cat.is_catch_all && (
                        <button
                          onClick={() => handleDeleteCategory(cat.id)}
                          aria-label={`Delete ${cat.name}`}
                          className="rounded-pill p-2 text-muted transition-colors hover:text-danger hover:bg-danger/10"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
