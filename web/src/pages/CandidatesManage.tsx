import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Candidate } from '../types';
import Toast from '../components/Toast';

interface ToastState {
  show: boolean;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

export default function CandidatesManage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [editingImageFor, setEditingImageFor] = useState<number | null>(null);
  const [toast, setToast] = useState<ToastState>({ show: false, message: '', type: 'info' });
  const navigate = useNavigate();

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    setToast({ show: true, message, type });
  };

  // Form state for manual candidate
  const [formData, setFormData] = useState({
    full_name: '',
    which_position: '',
    degree: '',
    image: '',
    election_time: '',
    description: ''
  });
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');

  useEffect(() => {
    fetchCandidates();
  }, []);

  const fetchCandidates = async () => {
    try {
      const response = await api.get('/candidates');
      setCandidates(response.data);
    } catch (error: any) {
      if (error.response?.status === 401) {
        navigate('/admin/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const syncCandidates = async () => {
    setSyncing(true);
    try {
      const response = await api.post('/candidates/sync-from-api');
      showToast(`${response.data.count} ta o'qituvchi sync qilindi!`, 'success');
      fetchCandidates();
    } catch (error) {
      showToast('Sync xatolik yuz berdi', 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        showToast('Faqat rasm fayllari qo\'shish mumkin!', 'warning');
        return;
      }
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        showToast('Rasm hajmi 5MB dan oshmasligi kerak!', 'warning');
        return;
      }
      setSelectedFile(file);
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const uploadImage = async () => {
    if (!selectedFile) return null;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await api.post('/candidates/upload-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data.image_url;
    } catch (error) {
      showToast('Rasmni yuklashda xatolik yuz berdi', 'error');
      return null;
    } finally {
      setUploading(false);
    }
  };

  const handleAddManual = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let imageUrl = formData.image?.trim() || undefined;

      // If a file is selected, upload it first
      if (selectedFile) {
        const uploadedUrl = await uploadImage();
        if (uploadedUrl) {
          imageUrl = uploadedUrl;
        } else {
          // Upload failed, don't proceed
          return;
        }
      }

      const payload: any = {
        full_name: formData.full_name,
        which_position: formData.which_position?.trim() || undefined,
        degree: formData.degree?.trim() || undefined,
        image: imageUrl,
        description: formData.description?.trim() || undefined,
      };

      if (formData.election_time?.trim()) {
        payload.election_time = formData.election_time.trim();
      }

      await api.post('/candidates/manual', payload);
      showToast('Kandidat qo\'shildi!', 'success');
      setShowAddModal(false);
      setFormData({ full_name: '', which_position: '', degree: '', image: '', election_time: '', description: '' });
      setSelectedFile(null);
      setImagePreview('');
      fetchCandidates();
    } catch (error) {
      showToast('Xatolik yuz berdi', 'error');
    }
  };

  const handleDeleteCandidate = async (candidateId: number, candidateName: string) => {
    if (!confirm(`${candidateName} nomzodni o'chirishni xohlaysizmi?`)) {
      return;
    }

    try {
      await api.delete(`/candidates/${candidateId}`);
      showToast('Kandidat o\'chirildi!', 'success');
      fetchCandidates();
    } catch (error: any) {
      if (error.response?.status === 401) {
        navigate('/admin/login');
      } else {
        showToast('Xatolik yuz berdi', 'error');
      }
    }
  };

  const handleUpdateImage = async (candidateId: number) => {
    if (!selectedFile) {
      showToast('Iltimos, rasm tanlang!', 'warning');
      return;
    }

    try {
      const uploadedUrl = await uploadImage();
      if (!uploadedUrl) return;

      await api.patch(`/candidates/${candidateId}`, { image: uploadedUrl });
      showToast('Rasm yangilandi!', 'success');
      setEditingImageFor(null);
      setSelectedFile(null);
      setImagePreview('');
      fetchCandidates();
    } catch (error: any) {
      if (error.response?.status === 401) {
        navigate('/admin/login');
      } else {
        showToast('Xatolik yuz berdi', 'error');
      }
    }
  };

  // Filter candidates based on search query
  const filteredCandidates = candidates.filter(candidate => {
    const query = searchQuery.toLowerCase();
    return (
      candidate.full_name.toLowerCase().includes(query) ||
      candidate.which_position?.toLowerCase().includes(query) ||
      candidate.degree?.toLowerCase().includes(query)
    );
  });

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Yuklanmoqda...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-800">Kandidatlarni Boshqarish</h1>
          <div className="space-x-4">
            <button
              onClick={syncCandidates}
              disabled={syncing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
            >
              {syncing ? 'Sync...' : 'API\'dan Sync'}
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Qo'lda Qo'shish
            </button>
            <button
              onClick={() => navigate('/admin/dashboard')}
              className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
            >
              Dashboard
            </button>
          </div>
        </div>
      </nav>

      {/* Search and Filters */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex-1 w-full md:max-w-md">
              <input
                type="text"
                placeholder="Ism, lavozim yoki daraja bo'yicha qidirish..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Ko'rinish:</span>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 rounded ${
                  viewMode === 'list'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                List
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 rounded ${
                  viewMode === 'grid'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Grid
              </button>
            </div>
          </div>
        </div>

        <h2 className="text-xl font-bold mb-4">
          Jami Kandidatlar: {filteredCandidates.length} / {candidates.length}
        </h2>

        {/* List View */}
        {viewMode === 'list' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rasm
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ism
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Lavozim
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Daraja
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Manba
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amallar
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredCandidates.map((candidate) => (
                  <tr key={candidate.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {candidate.image ? (
                          <img
                            src={candidate.image}
                            alt={candidate.full_name}
                            className="h-12 w-12 rounded-full object-cover"
                          />
                        ) : (
                          <div className="h-12 w-12 rounded-full bg-gray-300 flex items-center justify-center">
                            <span className="text-gray-600 text-xs">Rasm yo'q</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{candidate.full_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{candidate.which_position || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{candidate.degree || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        candidate.from_api
                          ? 'bg-green-100 text-green-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {candidate.from_api ? 'API' : 'Manual'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        {editingImageFor === candidate.id ? (
                          <>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={handleFileChange}
                              className="text-xs"
                            />
                            <button
                              onClick={() => handleUpdateImage(candidate.id)}
                              disabled={uploading}
                              className="text-green-600 hover:text-green-900 disabled:text-gray-400"
                            >
                              {uploading ? 'Yuklanmoqda...' : 'Saqlash'}
                            </button>
                            <button
                              onClick={() => {
                                setEditingImageFor(null);
                                setSelectedFile(null);
                                setImagePreview('');
                              }}
                              className="text-gray-600 hover:text-gray-900"
                            >
                              Bekor
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => setEditingImageFor(candidate.id)}
                              className="text-blue-600 hover:text-blue-900"
                              title="Rasm qo'shish/o'zgartirish"
                            >
                              {candidate.image ? 'Rasmni o\'zgartirish' : 'Rasm qo\'shish'}
                            </button>
                            {!candidate.from_api && (
                              <button
                                onClick={() => handleDeleteCandidate(candidate.id, candidate.full_name)}
                                className="text-red-600 hover:text-red-900"
                                title="O'chirish"
                              >
                                O'chirish
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredCandidates.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                Kandidatlar topilmadi
              </div>
            )}
          </div>
        )}

        {/* Grid View */}
        {viewMode === 'grid' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredCandidates.map((candidate) => (
              <div key={candidate.id} className="bg-white rounded-lg shadow p-4 relative">
                {candidate.image ? (
                  <img
                    src={candidate.image}
                    alt={candidate.full_name}
                    className="w-full h-48 object-cover rounded mb-3"
                  />
                ) : (
                  <div className="w-full h-48 bg-gray-300 rounded mb-3 flex items-center justify-center">
                    <span className="text-gray-600">Rasm yo'q</span>
                  </div>
                )}
                <h3 className="font-bold text-sm mb-2">{candidate.full_name}</h3>
                {candidate.which_position && (
                  <p className="text-xs text-gray-600 mb-1">{candidate.which_position}</p>
                )}
                {candidate.degree && (
                  <p className="text-xs text-gray-500">{candidate.degree}</p>
                )}
                {candidate.election_time && (
                  <p className="text-xs text-gray-500 mt-1">
                    Saylov vaqti: {candidate.election_time}
                  </p>
                )}
                {candidate.description && (
                  <p className="text-xs text-gray-500 mt-1 overflow-hidden text-ellipsis">
                    {candidate.description}
                  </p>
                )}
                <div className="mt-2 flex items-center justify-between">
                  <span className={`text-xs px-2 py-1 rounded ${
                    candidate.from_api
                      ? 'bg-green-100 text-green-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {candidate.from_api ? 'API' : 'Manual'}
                  </span>
                  {!candidate.from_api && (
                    <button
                      onClick={() => handleDeleteCandidate(candidate.id, candidate.full_name)}
                      className="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                      title="O'chirish"
                    >
                      O'chirish
                    </button>
                  )}
                </div>
              </div>
            ))}
            {filteredCandidates.length === 0 && (
              <div className="col-span-full text-center py-12 text-gray-500">
                Kandidatlar topilmadi
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add Manual Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Kandidat Qo'shish</h2>

            <form onSubmit={handleAddManual} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">To'liq Ism *</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Lavozim</label>
                <input
                  type="text"
                  value={formData.which_position}
                  onChange={(e) => setFormData({...formData, which_position: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Daraja</label>
                <input
                  type="text"
                  value={formData.degree}
                  onChange={(e) => setFormData({...formData, degree: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Rasm yuklash</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="w-full px-4 py-2 border rounded"
                />
                <p className="text-xs text-gray-500 mt-1">Maksimal hajm: 5MB</p>
                {imagePreview && (
                  <div className="mt-3">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="w-32 h-32 object-cover rounded-lg border-2 border-gray-300"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        setImagePreview('');
                      }}
                      className="mt-2 text-sm text-red-600 hover:text-red-700"
                    >
                      Rasmni o'chirish
                    </button>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Rasm URL (ixtiyoriy)</label>
                <input
                  type="text"
                  value={formData.image}
                  onChange={(e) => setFormData({...formData, image: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  placeholder="https://..."
                  disabled={!!selectedFile}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Fayl yuklanmagan bo'lsa URL kiritish mumkin
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Saylov vaqti</label>
                <input
                  type="text"
                  value={formData.election_time}
                  onChange={(e) => setFormData({...formData, election_time: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  placeholder="Masalan: 12:00 - 12:15"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Tavsif</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  rows={3}
                />
              </div>

              <div className="flex space-x-4 pt-4">
                <button
                  type="submit"
                  disabled={uploading}
                  className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {uploading ? 'Yuklanmoqda...' : 'Qo\'shish'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setFormData({ full_name: '', which_position: '', degree: '', image: '', election_time: '', description: '' });
                    setSelectedFile(null);
                    setImagePreview('');
                  }}
                  className="flex-1 bg-gray-600 text-white py-2 rounded hover:bg-gray-700"
                >
                  Bekor qilish
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast.show && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast({ ...toast, show: false })}
        />
      )}
    </div>
  );
}
