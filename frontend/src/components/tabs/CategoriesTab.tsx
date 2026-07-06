'use client';

import { useState } from 'react';
import { api } from '@/utils/api';
import { useApi, invalidate } from '@/utils/useApi';
import { Alert, Loading } from '@/components/ui';

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

  if (loading) {
    return <Loading label="Loading categories..." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Categories</h2>
        <p className="text-gray-600">Manage your spending categories</p>
      </div>

      {(error || loadError) && <Alert kind="error">{error || loadError}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}

      {/* Add Category Form */}
      <form onSubmit={handleAddCategory} className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            placeholder="Category name"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
          >
            Add
          </button>
        </div>
      </form>

      {/* Category List */}
      <div className="space-y-2">
        {categories.length === 0 ? (
          <p className="text-gray-600">No categories yet</p>
        ) : (
          categories.map((cat) => (
            <div key={cat.id} className="bg-white rounded-lg border border-gray-200 p-4 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <p className="font-medium text-gray-900">{cat.name}</p>
                {cat.is_catch_all && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    catch-all
                  </span>
                )}
              </div>
              {!cat.is_catch_all && (
                <button
                  onClick={() => handleDeleteCategory(cat.id)}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  Delete
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
