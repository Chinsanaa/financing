'use client';

import { useEffect, useState } from 'react';
import { api } from '@/utils/api';

interface Category {
  id: string;
  name: string;
  icon?: string;
  color?: string;
}

export default function CategoriesTab({ token }: { token: string }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await api.categories.list(token);
        setCategories(res.data.categories || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load categories');
      } finally {
        setLoading(false);
      }
    };

    loadCategories();
  }, [token]);

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCategoryName.trim()) return;

    try {
      setError('');
      setMessage('');
      const res = await api.categories.create(token, newCategoryName);
      setCategories([...categories, res.data.category]);
      setNewCategoryName('');
      setMessage('Category added!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add category');
    }
  };

  const handleDeleteCategory = async (id: string) => {
    if (!confirm('Delete this category? Transactions will be reassigned to "Other".')) return;

    try {
      await api.categories.delete(token, id);
      setCategories(categories.filter((c) => c.id !== id));
      setMessage('Category deleted');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete category');
    }
  };

  if (loading) {
    return <div className="text-gray-600">Loading categories...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Categories</h2>
        <p className="text-gray-600">Manage your spending categories</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {message && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {message}
        </div>
      )}

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
              <div>
                <p className="font-medium text-gray-900">{cat.name}</p>
                {cat.color && <p className="text-xs text-gray-500">{cat.color}</p>}
              </div>
              <button
                onClick={() => handleDeleteCategory(cat.id)}
                className="text-red-600 hover:text-red-700 text-sm"
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
