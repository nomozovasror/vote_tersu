import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Event, Candidate, TimerState, EventStatus } from '../types';
import { showSuccess, showError, showConfirm, showToast, showLoading, closeAlert } from '../utils/swal';

interface EventCandidate {
  id: number;
  candidate_id: number;
  order: number;
  status: string;
  candidate_group: string | null;
  candidate: Candidate;
}

interface CurrentCandidateInfo {
  candidate: Candidate | null;
  event_candidate_id?: number;
  index: number;
  total: number;
  timer?: TimerState;
}

export default function EventManage() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [eventCandidates, setEventCandidates] = useState<EventCandidate[]>([]);
  const [currentCandidate, setCurrentCandidate] = useState<CurrentCandidateInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingTimer, setStartingTimer] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState<Candidate | null>(null);
  const [editForm, setEditForm] = useState({
    which_position: '',
    election_time: '',
    description: ''
  });
  const [allCandidates, setAllCandidates] = useState<Candidate[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [selectedForGroup, setSelectedForGroup] = useState<number[]>([]);
  const [groupName, setGroupName] = useState('');
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [showEditEventModal, setShowEditEventModal] = useState(false);
  const [editEventName, setEditEventName] = useState('');
  const navigate = useNavigate();

  const formatDateTime = (value?: string | null) => {
    if (!value) return '';
    return value;
  };

  const timerRunning = currentCandidate?.timer?.running ?? false;
  const timerStarted = !!currentCandidate?.timer?.started_at;
  const timerRemainingMs = currentCandidate?.timer?.remaining_ms ?? 0;
  const timerRemainingSec = Math.max(0, Math.ceil(timerRemainingMs / 1000));
  const timerButtonDisabled = startingTimer || !currentCandidate?.candidate || timerRunning || event?.status !== EventStatus.ACTIVE;
  const missingPositionCount = eventCandidates.reduce((count, ec) => {
    const position = ec.candidate?.which_position || '';
    return !position.trim() ? count + 1 : count;
  }, 0);
  const canStartEvent = missingPositionCount === 0;
  useEffect(() => {
    fetchEventDetails();
    fetchCurrentCandidate();
    fetchAllCandidates();
    const interval = setInterval(fetchCurrentCandidate, 2000);
    return () => clearInterval(interval);
  }, [id]);

  const fetchEventDetails = async () => {
    try {
      const response = await api.get(`/events/${id}`);
      setEvent(response.data);

      // Fetch ordered event candidates
      const candidatesResp = await api.get(`/event-management/${id}/candidates`);
      setEventCandidates(candidatesResp.data);
    } catch (error: any) {
      if (error.response?.status === 401) {
        navigate('/admin/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentCandidate = async () => {
    try {
      const response = await api.get(`/event-management/${id}/current-candidate`);
      setCurrentCandidate(response.data);
    } catch (error) {
      console.error('Failed to fetch current candidate');
    }
  };

  const fetchAllCandidates = async () => {
    try {
      const response = await api.get('/candidates');
      setAllCandidates(response.data);
    } catch (error) {
      console.error('Failed to fetch candidates');
    }
  };

  const openEditModal = (candidate: Candidate) => {
    setEditingCandidate(candidate);
    setEditForm({
      which_position: candidate.which_position || '',
      election_time: candidate.election_time || '',
      description: candidate.description || ''
    });
    setShowEditModal(true);
  };

  const closeEditModal = () => {
    setShowEditModal(false);
    setEditingCandidate(null);
  };

  const saveCandidateDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCandidate) return;

    try {
      showLoading('Saqlanmoqda...');
      const whichPositionValue = editForm.which_position?.trim() || '';
      const payload: any = {
        which_position: whichPositionValue || null,
        description: editForm.description?.trim() ? editForm.description.trim() : null,
      };

      if (editForm.election_time?.trim()) {
        payload.election_time = editForm.election_time.trim();
      } else {
        payload.election_time = null;
      }

      await api.patch(`/candidates/${editingCandidate.id}`, payload);
      closeEditModal();
      fetchEventDetails();
      fetchCurrentCandidate();
      fetchAllCandidates();
      closeAlert();
      showToast('Kandidat ma\'lumotlari yangilandi', 'success');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || "Ma'lumotlarni yangilashda xatolik");
    }
  };

  const toggleCandidateSelection = (eventCandidateId: number) => {
    setSelectedForGroup(prev => {
      if (prev.includes(eventCandidateId)) {
        return prev.filter(id => id !== eventCandidateId);
      } else {
        if (prev.length >= 4) {
          showToast('Group uchun maksimal 4 ta kandidat tanlash mumkin!', 'warning');
          return prev;
        }
        return [...prev, eventCandidateId];
      }
    });
  };

  const openGroupModal = () => {
    if (selectedForGroup.length < 2) {
      showToast('Kamida 2 ta kandidat tanlang!', 'warning');
      return;
    }
    if (selectedForGroup.length > 4) {
      showToast('Group uchun maksimal 4 ta kandidat tanlash mumkin!', 'warning');
      return;
    }
    setGroupName(`Group-${Date.now()}`);
    setShowGroupModal(true);
  };

  const createGroup = async () => {
    if (!groupName.trim()) {
      showToast('Group nomini kiriting!', 'warning');
      return;
    }

    if (selectedForGroup.length < 2) {
      showToast('Kamida 2 ta kandidat tanlang!', 'warning');
      return;
    }

    try {
      showLoading('Group yaratilmoqda...');
      const currentGroupName = groupName.trim(); // Save group name before clearing state
      await api.post(`/event-management/${id}/set-group`, {
        event_candidate_ids: selectedForGroup,
        group_name: currentGroupName
      });

      closeAlert();
      setShowGroupModal(false);
      setSelectedForGroup([]);
      setGroupName('');
      fetchEventDetails();
      showToast(`Group "${currentGroupName}" yaratildi!`, 'success');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Group yaratishda xatolik');
    }
  };

  const startEvent = async () => {
    if (eventCandidates.length === 0) {
      showToast('Kamida bitta kandidat qo\'shing!', 'warning');
      return;
    }

    if (missingPositionCount > 0) {
      showError('Tanlov boshlashdan oldin barcha kandidatlar uchun qaysi lavozimga saylanishi kerakligini kiriting.');
      return;
    }

    const result = await showConfirm(
      'Tanlovni boshlashni tasdiqlaysizmi?',
      'Tanlov boshlash',
      'Ha, boshlash',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Tanlov boshlanmoqda...');
      await api.post(`/events/${id}/start`);
      fetchEventDetails();
      closeAlert();
      showSuccess('Event muvaffaqiyatli boshlandi!');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Tanlov boshlashda xatolik');
    }
  };

  const stopEvent = async () => {
    const result = await showConfirm(
      'Tanlovni to\'xtatishni tasdiqlaysizmi?',
      'Tanlov to\'xtatish',
      'Ha, to\'xtatish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Tanlov to\'xtatilmoqda...');
      await api.post(`/events/${id}/stop`);
      fetchEventDetails();
      closeAlert();
      showSuccess('Event to\'xtatildi');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Tanlovni to\'xtatishda xatolik');
    }
  };

  const resetEvent = async () => {
    const result = await showConfirm(
      'Tanlovni qayta boshlashni tasdiqlaysizmi? Barcha ovozlar va natijalar o\'chiriladi!',
      'Tanlovni Qayta Boshlash',
      'Ha, qayta boshlash',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Tanlov qayta boshlanmoqda...');
      await api.post(`/events/${id}/reset`);
      await fetchEventDetails();
      await fetchCurrentCandidate();
      closeAlert();
      showSuccess('Tanlov muvaffaqiyatli qayta boshlandi! Barcha ovozlar tozalandi.');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Tanlovni qayta boshlashda xatolik');
    }
  };

  const updateEventName = async () => {
    if (!editEventName.trim()) {
      showError('Tanlov nomini kiriting!');
      return;
    }

    try {
      showLoading('Tanlov nomi o\'zgartirilmoqda...');
      await api.put(`/events/${id}`, { name: editEventName });
      await fetchEventDetails();
      setShowEditEventModal(false);
      closeAlert();
      showSuccess('Tanlov nomi muvaffaqiyatli o\'zgartirildi!');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Tanlov nomini o\'zgartirishda xatolik');
    }
  };

  const openEditEventModal = () => {
    setEditEventName(event?.name || '');
    setShowEditEventModal(true);
  };

  const clearCandidateVotes = async (candidateId: number, candidateName: string) => {
    const result = await showConfirm(
      `${candidateName} uchun barcha ovozlarni o'chirmoqchimisiz?`,
      'Ovozlarni Bekor Qilish',
      'Ha, o\'chirish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Ovozlar o\'chirilmoqda...');
      const response = await api.delete(`/event-management/${id}/candidate/${candidateId}/votes`);
      closeAlert();
      showSuccess(`${response.data.deleted_count} ta ovoz o'chirildi`);
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Ovozlarni o\'chirishda xatolik');
    }
  };

  const clearGroupVotes = async (groupName: string) => {
    const result = await showConfirm(
      `"${groupName}" guruhidagi barcha kandidatlar uchun ovozlarni o'chirmoqchimisiz?`,
      'Guruh Ovozlarini Bekor Qilish',
      'Ha, o\'chirish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Guruh ovozlari o\'chirilmoqda...');
      const response = await api.delete(`/event-management/${id}/group/${encodeURIComponent(groupName)}/votes`);
      closeAlert();
      showSuccess(`${response.data.deleted_count} ta ovoz o'chirildi (${response.data.candidates_affected} kandidat)`);
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Guruh ovozlarini o\'chirishda xatolik');
    }
  };

  const goToCandidate = async (candidateIndex: number, candidateName: string) => {
    const result = await showConfirm(
      `"${candidateName}" ga o'tmoqchimisiz?`,
      'Kandidatga O\'tish',
      'Ha, o\'tish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('O\'tilmoqda...');
      await api.post(`/event-management/${id}/set-current-candidate/${candidateIndex}`);
      await fetchEventDetails();
      await fetchCurrentCandidate();
      closeAlert();
      showSuccess('Muvaffaqiyatli o\'tildi!');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Kandidatga o\'tishda xatolik');
    }
  };


  const viewResults = async () => {
    try {
      showLoading('Natijalar yuklanmoqda...');
      const response = await api.get(`/events/${id}/results`);
      setResults(response.data.results || []);
      closeAlert();
      setShowResultsModal(true);
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Natijalarni yuklashda xatolik');
    }
  };

  const downloadResults = async () => {
    try {
      showLoading('Fayl tayyorlanmoqda...');
      const response = await api.get(`/events/${id}/results/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${event?.name}_natijalar.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      closeAlert();
      showToast('Fayl muvaffaqiyatli yuklandi', 'success');
    } catch (error: any) {
      closeAlert();
      showError('Faylni yuklashda xatolik');
    }
  };

  const startTimer = async () => {
    try {
      setStartingTimer(true);
      await api.post(`/event-management/${id}/start-timer`);
      fetchCurrentCandidate();
      showToast('Timer ishga tushdi!', 'success');
    } catch (error: any) {
      showError(error.response?.data?.detail || 'Timer ishga tushirishda xatolik');
    } finally {
      setStartingTimer(false);
    }
  };

  const moveCandidate = async (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === eventCandidates.length - 1) return;

    const newOrder = [...eventCandidates];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    // Swap
    [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];

    // Update order values
    const reorderedIds = newOrder.map(ec => ec.candidate_id);

    try {
      await api.post(`/event-management/${id}/reorder-candidates`, {
        candidate_ids: reorderedIds
      });
      setEventCandidates(newOrder);
    } catch (error: any) {
      showError(error.response?.data?.detail || 'Tartibni o\'zgartirishda xatolik');
    }
  };

  const nextCandidate = async () => {
    const result = await showConfirm(
      'Keyingi kandidatga o\'tishni tasdiqlaysizmi?',
      'Tasdiqlash',
      'Ha, o\'tish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Keyingi kandidatga o\'tilmoqda...');
      await api.post(`/event-management/${id}/next-candidate`);
      await fetchEventDetails();  // Refresh to get updated candidate statuses
      await fetchCurrentCandidate();
      closeAlert();
      showToast('Keyingi kandidatga o\'tildi!', 'success');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Xatolik yuz berdi');
    }
  };

  const addCandidate = async (candidateId: number) => {
    try {
      showLoading('Kandidat qo\'shilmoqda...');
      await api.post(`/event-management/${id}/add-candidate/${candidateId}`);
      fetchEventDetails();
      closeAlert();
      showToast('Kandidat qo\'shildi!', 'success');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Xatolik yuz berdi');
    }
  };

  const removeCandidate = async (candidateId: number) => {
    const result = await showConfirm(
      'Bu kandidatni o\'chirmoqchimisiz?',
      'Kandidatni o\'chirish',
      'Ha, o\'chirish',
      'Bekor qilish'
    );

    if (!result.isConfirmed) return;

    try {
      showLoading('Kandidat o\'chirilmoqda...');
      await api.delete(`/event-management/${id}/remove-candidate/${candidateId}`);
      fetchEventDetails();
      closeAlert();
      showToast('Kandidat o\'chirildi!', 'success');
    } catch (error: any) {
      closeAlert();
      showError(error.response?.data?.detail || 'Xatolik yuz berdi');
    }
  };

  // Filter candidates - show only those not in event
  const eventCandidateIds = eventCandidates.map(ec => ec.candidate_id);
  const availableCandidates = allCandidates.filter(
    c => !eventCandidateIds.includes(c.id)
  );

  // Filter by search
  const filteredCandidates = availableCandidates.filter(c => {
    const positionValue = (c.which_position || '').toLowerCase();
    const query = searchQuery.toLowerCase();
    return (
      c.full_name.toLowerCase().includes(query) ||
      (positionValue && positionValue.includes(query))
    );
  });

  if (loading || !event) {
    return <div className="flex items-center justify-center h-screen">Yuklanmoqda...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-lg mb-8">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-800">{event.name}</h1>
            <button
              onClick={openEditEventModal}
              className="text-blue-600 hover:text-blue-700 p-2 rounded-lg hover:bg-blue-50 transition-all"
              title="Tanlov nomini o'zgartirish"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          </div>
          <button
            onClick={() => navigate('/admin/dashboard')}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
          >
            Dashboard
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4">
        {/* Event Controls */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-xl font-bold mb-6">Tanlov Boshqaruvi</h2>

          {/* Status Info */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-6 border border-blue-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Status</p>
                <p className="text-lg font-semibold capitalize flex items-center gap-2">
                  <span className={`w-3 h-3 rounded-full ${
                    event.status === EventStatus.PENDING ? 'bg-yellow-500' :
                    event.status === EventStatus.ACTIVE ? 'bg-green-500 animate-pulse' :
                    'bg-gray-500'
                  }`}></span>
                  {event.status === EventStatus.PENDING ? 'Kutilmoqda' :
                   event.status === EventStatus.ACTIVE ? 'Faol' :
                   event.status === EventStatus.FINISHED ? 'Tugallangan' : 'Arxivlangan'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Ajratilgan vaqt</p>
                <p className="text-lg font-semibold">{event.duration_sec} soniya</p>
              </div>
            </div>

            {currentCandidate && (
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-sm text-gray-600 mb-1">Joriy kandidat</p>
                <p className="text-lg font-semibold">
                  {currentCandidate.index + 1} / {currentCandidate.total}
                  {currentCandidate.candidate && (
                    <span className="ml-2 text-blue-600">— {currentCandidate.candidate.full_name}</span>
                  )}
                </p>
                {currentCandidate?.timer && currentCandidate.candidate && (
                  <p className="text-sm text-gray-600 mt-1">
                    Timer: <span className="font-semibold">
                      {timerRunning
                        ? `⏱️ Faol (${timerRemainingSec}s qoldi)`
                        : timerStarted
                        ? '✓ Yakunlangan'
                        : '○ Boshlanmagan'}
                    </span>
                  </p>
                )}
              </div>
            )}

            {event.status === EventStatus.PENDING && missingPositionCount > 0 && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-700 font-medium">
                  ⚠️ {missingPositionCount} ta kandidat uchun qaysi lavozimga saylanishi kerakligini kiriting.
                </p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            {event.status === EventStatus.PENDING && (
              <button
                onClick={startEvent}
                disabled={!canStartEvent}
                className={`px-6 py-3 rounded-lg font-semibold text-white transition-all shadow-md ${
                  canStartEvent
                    ? 'bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 hover:shadow-lg'
                    : 'bg-gray-400 cursor-not-allowed'
                }`}
              >
                ▶️ Tanlovni Boshlash
              </button>
            )}

            {event.status === EventStatus.ACTIVE && (
              <>
                <button
                  onClick={startTimer}
                  disabled={timerButtonDisabled}
                  className={`px-6 py-3 rounded-lg font-semibold text-white transition-all shadow-md ${
                    timerRunning
                      ? 'bg-green-600 cursor-not-allowed'
                      : timerButtonDisabled
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 hover:shadow-lg'
                  }`}
                >
                  {startingTimer ? '⏳ Ishga tushmoqda...' : timerRunning ? '⏱️ Timer ishlamoqda' : timerStarted ? '🔄 Timerni qayta boshlash' : '⏱️ Timer Start'}
                </button>
                <button
                  onClick={nextCandidate}
                  className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-lg hover:shadow-lg font-semibold transition-all"
                >
                  Keyingi Kandidat →
                </button>
                <button
                  onClick={stopEvent}
                  className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white px-6 py-3 rounded-lg hover:shadow-lg font-semibold transition-all"
                >
                  ⏹️ Tanlovni To'xtatish
                </button>
              </>
            )}

            <button
              onClick={viewResults}
              className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white px-6 py-3 rounded-lg hover:shadow-lg font-semibold transition-all"
            >
              📊 Natijalarni Ko'rish
            </button>

            {event?.status !== EventStatus.ARCHIVED && (
              <button
                onClick={resetEvent}
                className="bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 text-white px-6 py-3 rounded-lg hover:shadow-lg font-semibold transition-all ml-auto"
              >
                🔄 Tanlovni Qayta Boshlash
              </button>
            )}
          </div>
        </div>

        {/* Candidate Management */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">
              Kandidatlar ({eventCandidates.length} ta)
            </h2>
            {event.status === EventStatus.PENDING && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 font-semibold"
              >
                + Kandidat Qo'shish
              </button>
            )}
          </div>

          {eventCandidates.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
              <p className="text-yellow-800 text-lg mb-2">
                Hozircha kandidatlar yo'q
              </p>
              <p className="text-yellow-600 mb-4">
                Tanlov boshlash uchun kamida bitta kandidat qo'shing
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 font-semibold"
              >
                Kandidat Qo'shish
              </button>
            </div>
          ) : (
            <div>
              {/* Group Controls */}
              {event.status === EventStatus.PENDING && eventCandidates.length >= 2 && (
                <div className="mb-4 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-semibold text-gray-800">
                        Group qilish: {selectedForGroup.length} / 4 ta kandidat tanlandi
                      </p>
                      <p className="text-sm text-gray-600">
                        Bir nechta kandidatni group qilish uchun checkboxlarni belgilang (min: 2, max: 4)
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {selectedForGroup.length > 0 && (
                        <button
                          onClick={() => setSelectedForGroup([])}
                          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                        >
                          Tozalash
                        </button>
                      )}
                      <button
                        onClick={openGroupModal}
                        disabled={selectedForGroup.length < 2}
                        className={`px-4 py-2 rounded font-semibold ${
                          selectedForGroup.length < 2
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-green-600 text-white hover:bg-green-700'
                        }`}
                      >
                        Group Yaratish
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-3">
              {eventCandidates.map((ec, index) => (
                <div
                  key={ec.id}
                  className={`flex items-center gap-4 p-4 rounded-lg border-2 ${
                    currentCandidate?.event_candidate_id === ec.id
                      ? 'border-blue-500 bg-blue-50'
                      : ec.status === 'completed'
                      ? 'border-green-300 bg-green-50'
                      : selectedForGroup.includes(ec.id)
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 bg-white'
                  }`}
                >
                  {/* Checkbox for grouping (only in PENDING status) */}
                  {event.status === EventStatus.PENDING && (
                    <div className="flex-shrink-0">
                      <input
                        type="checkbox"
                        checked={selectedForGroup.includes(ec.id)}
                        onChange={() => toggleCandidateSelection(ec.id)}
                        className="w-5 h-5 cursor-pointer"
                      />
                    </div>
                  )}

                  {/* Order Number */}
                  <div className="flex-shrink-0 w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-xl font-bold">{index + 1}</span>
                  </div>

                  {/* Candidate Image */}
                  {ec.candidate.image && (
                    <img
                      src={ec.candidate.image}
                      alt={ec.candidate.full_name}
                      className="w-16 h-16 object-cover rounded"
                    />
                  )}

                  {/* Candidate Info */}
                  <div className="flex-1 space-y-1">
                    <p className="font-bold text-lg">{ec.candidate.full_name}</p>
                    {ec.candidate.which_position && (
                      <p className="text-sm text-gray-600">
                        {ec.candidate.which_position}
                      </p>
                    )}
                    {ec.candidate.degree && (
                      <p className="text-xs text-gray-500">{ec.candidate.degree}</p>
                    )}
                    {ec.candidate.election_time && (
                      <p className="text-xs text-gray-500">
                        Saylov vaqti: {formatDateTime(ec.candidate.election_time)}
                      </p>
                    )}
                    {ec.candidate.description && (
                      <p className="text-xs text-gray-500">{ec.candidate.description}</p>
                    )}
                    {ec.candidate_group && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs font-semibold">
                          🔗 Group: {ec.candidate_group}
                        </span>
                        {/* Clear group votes button - only show if event is not finished or archived */}
                        {event.status !== EventStatus.FINISHED && event.status !== EventStatus.ARCHIVED && (
                          <button
                            onClick={() => clearGroupVotes(ec.candidate_group!)}
                            className="bg-red-100 text-red-700 hover:bg-red-200 px-2 py-1 rounded text-xs font-semibold transition-all flex items-center gap-1"
                            title="Guruh ovozlarini tozalash"
                          >
                            <span>🗑️</span>
                            <span>Guruh ovozlarini tozalash</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Status Badge */}
                  <div>
                    {currentCandidate?.event_candidate_id === ec.id && (
                      <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
                        Joriy
                      </span>
                    )}
                    {ec.status === 'completed' && currentCandidate?.event_candidate_id !== ec.id && (
                      <span className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
                        Yakunlandi
                      </span>
                    )}
                    {ec.status === 'pending' && currentCandidate?.event_candidate_id !== ec.id && (
                      <span className="bg-gray-300 text-gray-700 px-3 py-1 rounded-full text-sm font-semibold">
                        Kutilmoqda
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col gap-2 items-end">
                    <div className="flex gap-2">
                      {/* Go to Candidate Button - only show if event is active and not current */}
                      {event.status === EventStatus.ACTIVE && currentCandidate && currentCandidate.event_candidate_id !== ec.id && (
                        <button
                          onClick={() => goToCandidate(index, ec.candidate.full_name)}
                          className="px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm transition-all"
                          title="Bu kandidatga o'tish"
                        >
                          ➡️
                        </button>
                      )}
                      {/* Edit button - only show if event is not finished or archived */}
                      {event.status !== EventStatus.FINISHED && event.status !== EventStatus.ARCHIVED && (
                        <button
                          onClick={() => openEditModal(ec.candidate)}
                          className="px-3 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 text-sm transition-all"
                          title="Tahrirlash"
                        >
                          ✏️
                        </button>
                      )}
                      {/* Clear votes button - only show if event is not finished or archived */}
                      {event.status !== EventStatus.FINISHED && event.status !== EventStatus.ARCHIVED && (
                        <button
                          onClick={() => clearCandidateVotes(ec.candidate.id, ec.candidate.full_name)}
                          className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 text-sm transition-all"
                          title="Ovozlarni tozalash"
                        >
                          🗑️
                        </button>
                      )}
                    </div>

                    {/* Action Buttons */}
                    {event.status === EventStatus.PENDING && (
                      <div className="flex gap-2">
                        {/* Reorder Buttons */}
                        <div className="flex flex-col gap-1">
                          <button
                            onClick={() => moveCandidate(index, 'up')}
                            disabled={index === 0}
                            className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                            title="Yuqoriga"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => moveCandidate(index, 'down')}
                            disabled={index === eventCandidates.length - 1}
                            className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                            title="Pastga"
                          >
                            ▼
                          </button>
                        </div>

                        {/* Remove Button */}
                        <button
                          onClick={() => removeCandidate(ec.candidate_id)}
                          className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                          title="O'chirish"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-6">
          <h3 className="text-lg font-bold text-blue-900 mb-2">Yo'riqnoma:</h3>
          <ol className="list-decimal list-inside space-y-1 text-blue-800">
            <li>"+ Kandidat Qo'shish" tugmasi bilan kandidatlar qo'shing</li>
            <li>▲▼ tugmalar yordamida tartibni belgilang</li>
            <li>"Tanlov Boshlash" tugmasi bilan tanlovni faollashtiring</li>
            <li>Har bir kandidat uchun {event.duration_sec} soniya ajratiladi</li>
            <li>"Timer Start" tugmasi orqali ovoz berishni boshlang</li>
            <li>"Keyingi Kandidat" tugmasi bilan navbatdagi kandidatga o'ting</li>
            <li>Barcha kandidatlar yakunlangandan keyin tanlovni to'xtating</li>
          </ol>
        </div>
      </div>

      {/* Add Candidate Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Kandidat Qo'shish</h2>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setSearchQuery('');
                }}
                className="text-gray-500 hover:text-gray-700 text-3xl leading-none"
              >
                ×
              </button>
            </div>

            {/* Search */}
            <div className="mb-6">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ism bo'yicha qidiring..."
                className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
            </div>

            {/* Available Candidates */}
            {filteredCandidates.length === 0 ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                <p className="text-gray-600">
                  {searchQuery
                    ? 'Hech narsa topilmadi'
                    : 'Barcha kandidatlar allaqachon qo\'shilgan'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                {filteredCandidates.map(candidate => (
                  <div
                    key={candidate.id}
                    onClick={() => {
                      addCandidate(candidate.id);
                      setShowAddModal(false);
                      setSearchQuery('');
                    }}
                    className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-blue-50 hover:border-blue-500 transition-all"
                  >
                    {candidate.image && (
                      <img
                        src={candidate.image}
                        alt={candidate.full_name}
                        className="w-12 h-12 object-cover rounded"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{candidate.full_name}</p>
                      {candidate.which_position && (
                        <p className="text-xs text-gray-600 truncate">{candidate.which_position}</p>
                      )}
                    </div>
                    <span className="text-blue-600 text-xl">+</span>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 text-sm text-gray-600 text-center">
              Jami: {filteredCandidates.length} ta kandidat mavjud
            </div>
          </div>
        </div>
      )}

      {showEditModal && editingCandidate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-lg w-full">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">{editingCandidate.full_name} — ma'lumotlar</h2>
              <button
                onClick={closeEditModal}
                className="text-gray-500 hover:text-gray-700 text-3xl leading-none"
              >
                ×
              </button>
            </div>

            <form onSubmit={saveCandidateDetails} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Qaysi Lavozimga *</label>
                <input
                  type="text"
                  value={editForm.which_position}
                  onChange={(e) => setEditForm({...editForm, which_position: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Saylov vaqti</label>
                <input
                  type="text"
                  value={editForm.election_time}
                  onChange={(e) => setEditForm({...editForm, election_time: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  placeholder="Masalan: 12:00 - 12:15"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Tavsif</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({...editForm, description: e.target.value})}
                  className="w-full px-4 py-2 border rounded"
                  rows={4}
                />
              </div>

              <div className="flex gap-4 pt-4 justify-end">
                <button
                  type="button"
                  onClick={closeEditModal}
                  className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Group Creation Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg max-w-lg w-full">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Group Yaratish</h2>
              <button
                onClick={() => setShowGroupModal(false)}
                className="text-gray-500 hover:text-gray-700 text-3xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              {/* Selected Candidates List */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Tanlangan kandidatlar ({selectedForGroup.length} ta):
                </label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-40 overflow-y-auto">
                  <ul className="space-y-2">
                    {selectedForGroup.map(ecId => {
                      const ec = eventCandidates.find(ec => ec.id === ecId);
                      return ec ? (
                        <li key={ec.id} className="flex items-center gap-2">
                          <span className="text-green-600">✓</span>
                          <span className="font-medium">{ec.candidate.full_name}</span>
                          {ec.candidate.which_position && (
                            <span className="text-sm text-gray-600">
                              ({ec.candidate.which_position})
                            </span>
                          )}
                        </li>
                      ) : null;
                    })}
                  </ul>
                </div>
              </div>

              {/* Group Name Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Group nomi *
                </label>
                <input
                  type="text"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Masalan: Rektor-2024, Dekan-Matematika"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">
                  Bu nom faqat boshqaruv uchun, ovoz beruvchilar ko'rmaydi
                </p>
              </div>

              {/* Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm text-blue-800">
                  ℹ️ Ovoz berish paytida bu kandidatlar birgalikda ko'rsatiladi.
                  Ovoz beruvchi bittasini tanlaydi va tanlangan "Ha",
                  qolganlar "Yo'q" ovoz oladi.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-4 justify-end">
                <button
                  type="button"
                  onClick={() => {
                    setShowGroupModal(false);
                    setGroupName('');
                  }}
                  className="px-6 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 font-semibold"
                >
                  Bekor qilish
                </button>
                <button
                  type="button"
                  onClick={createGroup}
                  className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-semibold"
                >
                  Group Yaratish
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results Modal */}
      {showResultsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-7xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center">
              <h2 className="text-2xl font-bold">Ovoz Berish Natijalari</h2>
              <button
                onClick={() => setShowResultsModal(false)}
                className="text-gray-500 hover:text-gray-700 text-3xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="p-6">
              <div className="mb-4 flex gap-3 justify-end">
                <button
                  onClick={downloadResults}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  📥 Word Yuklab Olish
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-gray-300">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="border border-gray-300 px-4 py-2">T/r</th>
                      <th className="border border-gray-300 px-4 py-2">Lavozim</th>
                      <th className="border border-gray-300 px-4 py-2">Nomzodlar</th>
                      <th className="border border-gray-300 px-4 py-2">Ovoz berishda qatnashganlar soni</th>
                      <th className="border border-gray-300 px-4 py-2">Rozi</th>
                      <th className="border border-gray-300 px-4 py-2">Qarshi</th>
                      <th className="border border-gray-300 px-4 py-2">Betaraf</th>
                      <th className="border border-gray-300 px-4 py-2">Natija</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((result) => {
                      // Calculate participants for this candidate (yes + no + neutral)
                      const candidateParticipants = (result.yes_votes || 0) + (result.no_votes || 0) + (result.neutral_votes || 0);

                      return (
                        <tr key={result.candidate_id} className="hover:bg-gray-50">
                          <td className="border border-gray-300 px-4 py-2 text-center">{result.row_number}</td>
                          <td className="border border-gray-300 px-4 py-2">{result.which_position || '-'}</td>
                          <td className="border border-gray-300 px-4 py-2">
                            <div className="flex items-center gap-3">
                              {result.image && (
                                <img
                                  src={result.image}
                                  alt={result.full_name}
                                  className="w-12 h-12 rounded-full object-cover border-2 border-gray-300"
                                />
                              )}
                              <span>{result.full_name}</span>
                            </div>
                          </td>
                          <td className="border border-gray-300 px-4 py-2 text-center">{candidateParticipants}</td>
                          <td className="border border-gray-300 px-4 py-2 text-center">
                            {result.yes_votes}<br />({result.yes_percent}%)
                          </td>
                          <td className="border border-gray-300 px-4 py-2 text-center">
                            {result.no_votes}<br />({result.no_percent}%)
                          </td>
                          <td className="border border-gray-300 px-4 py-2 text-center">
                            {result.neutral_votes}<br />({result.neutral_percent}%)
                          </td>
                          <td className="border border-gray-300 px-4 py-2 text-center font-semibold">
                            {result.result}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {results.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  Hozircha natijalar mavjud emas
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit Event Name Modal */}
      {showEditEventModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-6">
              <h2 className="text-2xl font-bold text-white flex items-center">
                <svg className="w-7 h-7 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Tanlov Nomini O'zgartirish
              </h2>
              <p className="text-blue-100 text-sm mt-1">Yangi nom kiriting</p>
            </div>

            {/* Modal Body */}
            <div className="p-8 space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Tanlov Nomi *
                </label>
                <input
                  type="text"
                  value={editEventName}
                  onChange={(e) => setEditEventName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Tanlov nomini kiriting"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      updateEventName();
                    }
                  }}
                />
              </div>

              <div className="flex space-x-3 pt-2">
                <button
                  onClick={updateEventName}
                  className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-md hover:shadow-lg transition-all"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Saqlash
                </button>
                <button
                  onClick={() => setShowEditEventModal(false)}
                  className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-gray-300 text-base font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-all"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
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
