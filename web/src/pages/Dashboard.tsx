import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Event, EventStatus } from '../types';

export default function Dashboard() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [eventName, setEventName] = useState('');
  const [durationSec, setDurationSec] = useState(15);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const eventsRes = await api.get('/events');
      setEvents(eventsRes.data);
    } catch (error: any) {
      if (error.response?.status === 401) {
        navigate('/admin/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/admin/login');
  };

  const createEvent = async () => {
    if (!eventName.trim()) {
      alert('Event nomini kiriting!');
      return;
    }

    try {
      const response = await api.post('/events', {
        name: eventName,
        candidate_ids: [],
        duration_sec: durationSec
      });
      alert('Event muvaffaqiyatli yaratildi! Endi kandidatlarni qo\'shing.');
      setShowCreateModal(false);
      setEventName('');
      setDurationSec(15);
      // Navigate to event manage page
      navigate(`/admin/event/${response.data.id}`);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Event yaratishda xatolik yuz berdi');
    }
  };

  const copyVoteLink = (link: string) => {
    const url = `${window.location.origin}/vote/${link}`;
    navigator.clipboard.writeText(url);
    alert('Vote link copied!');
  };

  const copyDisplayLink = (link: string) => {
    const url = `${window.location.origin}/display/${link}`;
    navigator.clipboard.writeText(url);
    alert('Display link copied!');
  };

  const archiveEvent = async (eventId: number) => {
    if (!confirm('Eventni arxivga o\'tkazmoqchimisiz? Event faqat ko\'rish rejimida qoladi.')) {
      return;
    }

    try {
      const response = await api.post(`/events/${eventId}/archive`);
      setEvents(prev => prev.map(event =>
        event.id === eventId ? response.data : event
      ));
      alert('Event arxivlandi.');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Eventni arxivlashda xatolik yuz berdi');
    }
  };

  const deleteEvent = async (eventId: number) => {
    if (!confirm('Bu eventni o\'chirmoqchimisiz? Barcha natijalar o\'chiriladi.')) {
      return;
    }

    try {
      await api.delete(`/events/${eventId}`);
      setEvents(prev => prev.filter(event => event.id !== eventId));
      alert('Event o\'chirildi.');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Eventni o\'chirishda xatolik yuz berdi');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-800">Admin Dashboard</h1>
          <div className="space-x-4">
            <button
              onClick={() => navigate('/admin/candidates')}
              className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
            >
              Kandidatlar Boshqaruvi
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Event Yaratish
            </button>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              Chiqish
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-6">Events</h2>

        <div className="grid gap-4">
          {events.map(event => (
            <div key={event.id} className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-semibold">{event.name}</h3>
                  <p className="text-gray-600">Status: {event.status}</p>
                  <p className="text-gray-600">Duration: {event.duration_sec}s</p>
                </div>
                <div className="flex flex-wrap gap-2 justify-end">
                  <button
                    onClick={() => navigate(`/admin/event/${event.id}`)}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                  >
                    Manage
                  </button>
                  <button
                    onClick={() => copyVoteLink(event.link)}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                  >
                    Copy Vote Link
                  </button>
                  <button
                    onClick={() => copyDisplayLink(event.link)}
                    className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                  >
                    Copy Display Link
                  </button>
                  {event.status !== EventStatus.ARCHIVED && (
                    <button
                      onClick={() => archiveEvent(event.id)}
                      className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
                    >
                      Archive
                    </button>
                  )}
                  <button
                    onClick={() => deleteEvent(event.id)}
                    className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Create Event Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-md w-full">
            <h2 className="text-2xl font-bold mb-6">Yangi Event Yaratish</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Event Nomi *</label>
                <input
                  type="text"
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Masalan: O'qituvchilar Kengashi 2025"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Har bir kandidat uchun vaqt (soniya) *
                </label>
                <input
                  type="number"
                  value={durationSec}
                  onChange={(e) => setDurationSec(parseInt(e.target.value) || 15)}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="5"
                  max="300"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Ovoz berish uchun berilgan vaqt
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  💡 Event yaratilgandan so'ng kandidatlarni qo'shish sahifasiga o'tasiz
                </p>
              </div>

              <div className="flex space-x-4 pt-4">
                <button
                  onClick={createEvent}
                  className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 font-semibold"
                >
                  Yaratish
                </button>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setEventName('');
                    setDurationSec(15);
                  }}
                  className="flex-1 bg-gray-600 text-white py-2 rounded hover:bg-gray-700"
                >
                  Bekor qilish
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
