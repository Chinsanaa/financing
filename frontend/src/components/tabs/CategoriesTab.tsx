'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Tags, Trash2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert } from '@/components/ui';
import Button from '@/components/ui/Button';
import Card, { SectionHeader } from '@/components/ui/Card';
import Badge, { categoryColor } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRows } from '@/components/ui/Skeleton';

interface Category {
  id: string;
  name: string;
  is_catch_all?: boolean;
}

export default function CategoriesTab() {
  const { data, setData, loading, error: loadError } = useApi<{ categories: Category[] }>('/categories/');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

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

  return (
    <div className="max-w-2xl space-y-6">
      <SectionHeader label="Model" title="Categories" />
      <p className="-mt-4 text-sm text-muted">
        The labels your model learns to predict. Keep them broad enough to be learnable.
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
        <div className="space-y-2">
          <AnimatePresence initial={false}>
            {categories.map((cat) => (
              <motion.div
                key={cat.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -24 }}
                transition={{ duration: 0.2 }}
              >
                <Card className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <Badge tone={categoryColor(cat.name)}>{cat.name}</Badge>
                    {cat.is_catch_all && <Badge tone="neutral">catch-all</Badge>}
                  </div>
                  {!cat.is_catch_all && (
                    <button
                      onClick={() => handleDeleteCategory(cat.id)}
                      aria-label={`Delete ${cat.name}`}
                      className="rounded-pill p-2 text-muted transition-colors hover:text-danger hover:bg-danger/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
