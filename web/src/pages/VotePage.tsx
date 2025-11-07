import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import api, { WS_BASE_URL } from '../utils/api';
import { Event, CurrentCandidate, EventStatus, VoteTally } from '../types';
import { generateUUID } from '../utils/uuid';
import { getDeviceId } from '../utils/deviceId';

export default function VotePage() {
  const { link } = useParams<{ link: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [currentCandidate, setCurrentCandidate] = useState<CurrentCandidate | null>(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const nonce = useRef(generateUUID());
  const deviceId = useRef(getDeviceId());
  const previousCandidateId = useRef<number | null>(null);
  const countdownTarget = useRef<number | null>(null);
  const [countdownMs, setCountdownMs] = useState(0);
  const [results, setResults] = useState<VoteTally[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState('');
  const [totalVotes, setTotalVotes] = useState(0);
  const resultsFetched = useRef(false);

  const formatDateTime = (value?: string | null) => {
    if (!value) return '';
    return value;
  };

  useEffect(() => {
    setResults([]);
    setTotalVotes(0);
    setResultsError('');
    resultsFetched.current = false;
    previousCandidateId.current = null;
    fetchEvent();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [link]);

  useEffect(() => {
    const timer = currentCandidate?.timer;
    if (!timer) {
      countdownTarget.current = null;
      setCountdownMs(0);
      return;
    }

    const remainingMs = typeof timer.remaining_ms === 'number' ? timer.remaining_ms : 0;
    const nowMs = Date.now();
    const endsAtMsFromTimer =
      typeof timer.ends_at_ts === 'number'
        ? timer.ends_at_ts
        : timer.ends_at
        ? new Date(timer.ends_at).getTime()
        : null;

    const targetMs =
      endsAtMsFromTimer && endsAtMsFromTimer > nowMs
        ? endsAtMsFromTimer
        : timer.running && remainingMs > 0
        ? nowMs + remainingMs
        : null;

    countdownTarget.current = targetMs;
    setCountdownMs(remainingMs);
  }, [
    currentCandidate?.timer?.started_at,
    currentCandidate?.timer?.running,
    currentCandidate?.timer?.ends_at,
    currentCandidate?.timer?.ends_at_ts,
    currentCandidate?.timer?.remaining_ms,
    currentCandidate?.candidate?.id,
  ]);

  useEffect(() => {
    if (!currentCandidate?.timer?.running || !countdownTarget.current) {
      return;
    }

    const tick = () => {
      if (!countdownTarget.current) {
        return;
      }
      const remaining = countdownTarget.current - Date.now();
      if (remaining <= 0) {
        setCountdownMs(0);
        countdownTarget.current = null;
      } else {
        setCountdownMs(remaining);
      }
    };

    tick();
    const interval = window.setInterval(tick, 250);
    return () => window.clearInterval(interval);
  }, [
    currentCandidate?.timer?.running,
    currentCandidate?.timer?.started_at,
    currentCandidate?.timer?.ends_at_ts,
  ]);

  useEffect(() => {
    if (!event?.id) return;

    const total = currentCandidate?.total ?? 0;
    const index = currentCandidate?.index ?? 0;
    const hasCandidate = !!currentCandidate?.candidate;
    const finished = event.status === EventStatus.FINISHED || event.status === EventStatus.ARCHIVED;
    const allDone = !hasCandidate && total > 0 && index >= total;

    if ((finished || allDone) && !resultsFetched.current && !resultsLoading) {
      fetchResults(event.id);
      if (!finished && allDone) {
        setEvent((prev) => prev ? { ...prev, status: EventStatus.FINISHED } : prev);
      }
    }
  }, [
    event?.id,
    event?.status,
    currentCandidate?.candidate,
    currentCandidate?.index,
    currentCandidate?.total,
    resultsLoading,
  ]);

  const fetchEvent = async () => {
    try {
      const response = await api.get(`/events/by-link/${link}`);
      setEvent(response.data);
    } catch (error) {
      setError('Event topilmadi');
    } finally {
      setLoading(false);
    }
  };

  const fetchResults = async (eventId: number) => {
    setResultsLoading(true);
    setResultsError('');
    try {
      const response = await api.get(`/events/${eventId}/results`);
      setResults(response.data?.results || []);
      setTotalVotes(response.data?.total_votes || 0);
      resultsFetched.current = true;
    } catch (err) {
      console.error('Failed to load results', err);
      setResultsError('Natijalarni olishda xatolik yuz berdi');
      resultsFetched.current = true;
    } finally {
      setResultsLoading(false);
    }
  };

  const connectWebSocket = () => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/vote/${link}`);

    ws.onopen = () => {
      console.log('WebSocket ulandi');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'current_candidate') {
        const newCandidate = data.data as CurrentCandidate | null;

        const incomingId = newCandidate?.candidate?.id ?? null;

        let candidateChanged = false;
        if (incomingId !== null) {
          if (previousCandidateId.current !== incomingId) {
            candidateChanged = true;
          }
          previousCandidateId.current = incomingId;
        } else {
          if (previousCandidateId.current !== null) {
            candidateChanged = true;
          }
          previousCandidateId.current = null;
        }

        if (candidateChanged) {
          setHasVoted(false);
          setSelectedCandidateId(null);
          nonce.current = generateUUID();
        }

        setCurrentCandidate(newCandidate);

        // Check if voting has completed (no candidate and index >= total)
        const total = newCandidate?.total ?? 0;
        const index = newCandidate?.index ?? 0;
        const hasCandidate = !!newCandidate?.candidate;
        if (!hasCandidate && total > 0 && index >= total) {
          // Update event status to finished
          setEvent((prev) => prev ? { ...prev, status: EventStatus.FINISHED } : prev);
        }
      } else if (data.type === 'vote_confirmed') {
        setHasVoted(true);
      } else if (data.type === 'error') {
        alert(data.message);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket xato:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket yopildi');
      // Reconnect after 3 seconds
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          connectWebSocket();
        }
      }, 3000);
    };

    wsRef.current = ws;
  };

  const castVote = (voteType: 'yes' | 'no' | 'neutral', targetCandidateId?: number) => {
    const timer = currentCandidate?.timer;
    if (!currentCandidate?.candidate || !timer?.running || timer.remaining_ms <= 0) {
      alert('Hozir ovoz berish faollashtirilmagan');
      return;
    }

    // If grouped voting and target candidate specified, vote for that specific candidate
    const candidateIdToVote = targetCandidateId || currentCandidate.candidate.id;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'cast_vote',
        vote_type: voteType,
        candidate_id: candidateIdToVote,
        nonce: nonce.current,
        device_id: deviceId.current
      }));
    } else {
      alert('Aloqa uzildi, sahifani yangilang');
    }
  };

  const retryFetchResults = () => {
    if (!event?.id) return;
    resultsFetched.current = false;
    fetchResults(event.id);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="text-xl">Yuklanmoqda...</div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="text-xl text-red-600">{error || 'Event topilmadi'}</div>
      </div>
    );
  }

  if (event.status === EventStatus.PENDING) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 px-4">
        <div className="text-center">
          <div className="text-2xl md:text-3xl font-bold text-yellow-600 mb-4">
            Bu event hozir faol emas
          </div>
          <p className="text-gray-600">Admin tomonidan event boshlanishini kuting</p>
        </div>
      </div>
    );
  }

  const eventFinished = event.status === EventStatus.FINISHED || event.status === EventStatus.ARCHIVED;
  const totalCandidates = currentCandidate?.total ?? 0;
  const currentIndex = currentCandidate?.index ?? 0;
  const allCandidatesDone = !currentCandidate?.candidate && totalCandidates > 0 && currentIndex >= totalCandidates;
  const shouldShowFinalResults = eventFinished || allCandidatesDone;

  const renderResultsSection = () => (
    <div className="space-y-6">
      {/* Completion Message */}
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl shadow-2xl p-8 md:p-12 text-center">
        <div className="text-6xl md:text-8xl mb-4">🎉</div>
        <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
          Ovoz berish yakunlandi!
        </h1>
        <p className="text-xl md:text-2xl text-white/90 mb-2">
          Barcha nomzodlar bo'yicha ovoz berish muvaffaqiyatli yakunlandi
        </p>
        <p className="text-lg md:text-xl text-white/80">
          Quyida yakuniy natijalar bilan tanishing
        </p>
      </div>

      {/* Results */}
      <div className="bg-white rounded-xl shadow-2xl p-6 md:p-8">
        <h2 className="text-xl md:text-2xl font-bold mb-4 text-center text-purple-800">📊 Yakuniy natijalar</h2>
        {resultsLoading || !resultsFetched.current ? (
          <div className="text-center text-gray-600 py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mb-3"></div>
            <p>Natijalar yuklanmoqda...</p>
          </div>
        ) : resultsError ? (
          <div className="text-center py-8">
            <p className="text-red-600 mb-3">{resultsError}</p>
            <button
              onClick={retryFetchResults}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
            >
              🔄 Qayta urinib ko'rish
            </button>
          </div>
        ) : results.length > 0 ? (
        <div className="space-y-3">
          {results.map((item, index) => (
            <div
              key={item.candidate_id}
              className="flex items-center justify-between bg-gradient-to-r from-blue-50 to-purple-50 border border-purple-200 rounded-xl px-4 py-4 hover:shadow-lg transition-all"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl md:text-2xl font-bold text-purple-700 min-w-[2rem]">{index + 1}.</span>
                {item.image && (
                  <img
                    src={item.image}
                    alt={item.full_name}
                    className="w-12 h-12 md:w-14 md:h-14 rounded-full object-cover border-2 border-purple-300 shadow-md"
                  />
                )}
                <div>
                  <p className="font-semibold text-base md:text-lg text-gray-800">{item.full_name}</p>
                  {item.which_position && (
                    <p className="text-xs md:text-sm text-blue-600 font-medium">{item.which_position}</p>
                  )}
                  {item.election_time && (
                    <p className="text-xs text-gray-500">{formatDateTime(item.election_time)}</p>
                  )}
                  <p className="text-sm md:text-base text-green-600 font-semibold mt-1">{item.percent.toFixed(1)}%</p>
                  {item.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-1">{item.description}</p>
                  )}
                </div>
              </div>
              <div className="text-lg md:text-2xl font-bold text-white bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 rounded-lg shadow-md">
                {item.votes}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-gray-600 py-8">
          <p className="text-xl">📭</p>
          <p className="mt-2">Natijalar mavjud emas.</p>
        </div>
      )}
      {!resultsLoading && !resultsError && results.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <p className="text-center text-base text-gray-700 font-medium">
            Jami ishtirokchilar: <span className="text-purple-700 font-bold">{totalVotes}</span>
          </p>
        </div>
      )}
      </div>
    </div>
  );

  // Check timer status FIRST before accessing candidate data
  const timer = currentCandidate?.timer;
  const timerStarted = !!timer?.started_at;
  const hasCandidate = !!currentCandidate?.candidate;

  // Don't show candidate info until timer starts
  if (hasCandidate && !timerStarted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 px-4">
        <div className="text-center bg-white rounded-2xl shadow-2xl p-12 max-w-md">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Navbatdagi kandidat</h2>
          <p className="text-sm text-gray-500">
            Admin tomonidan timer start qilinishini kuting
          </p>
        </div>
      </div>
    );
  }

  if (!hasCandidate) {
    if (shouldShowFinalResults) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-4 md:py-8 px-4">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-xl p-4 md:p-6 mb-4 md:mb-6 text-center">
              <h1 className="text-xl md:text-3xl font-bold mb-2">{event.name}</h1>
            </div>
            {renderResultsSection()}
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 px-4">
        <div className="text-center">
          <div className="text-2xl md:text-3xl font-bold mb-4">Ovoz berish kutilmoqda...</div>
          <p className="text-gray-600">Admin tomonidan kandidat tanlanishini kuting</p>
        </div>
      </div>
    );
  }

  // Only access candidate data after timer has started (we know it exists because hasCandidate is true)
  const candidate = currentCandidate.candidate!;
  const votingActive = !!timer?.running && timer.remaining_ms > 0;
  const remainingSeconds = Math.max(0, Math.ceil(countdownMs / 1000));
  const progressPercent = timer?.duration_sec
    ? Math.max(0, Math.min(100, (countdownMs / (timer.duration_sec * 1000)) * 100))
    : 0;
  const relatedCandidates = currentCandidate.related_candidates || [];
  const hasAlternatives = relatedCandidates.length > 1;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-4 md:py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Event Info */}
        <div className="bg-white rounded-xl shadow-xl p-4 md:p-6 mb-4 md:mb-6">
          <h1 className="text-xl md:text-3xl font-bold text-center mb-2">{event.name}</h1>
          <p className="text-center text-gray-600 text-sm md:text-base">
            Kandidat {currentCandidate.index + 1} / {currentCandidate.total}
          </p>
        </div>

        {/* Current Candidate or Grouped Candidates */}
        <div className="bg-white rounded-xl shadow-2xl p-6 md:p-8 mb-6">
          {/* Show individual candidate info only if not grouped */}
          {!hasAlternatives && (
            <>
              <div className="flex flex-col items-center mb-6 md:mb-8">
                {candidate.image && (
                  <img
                    src={candidate.image}
                    alt={candidate.full_name}
                    className="w-32 h-32 md:w-48 md:h-48 object-cover rounded-2xl shadow-lg mb-4"
                  />
                )}
                <div className="text-center">
                  <h2 className="text-xl md:text-3xl font-bold mb-2">{candidate.full_name}</h2>
                  {candidate.which_position && (
                    <p className="text-base md:text-lg text-gray-700 mb-1">{candidate.which_position}</p>
                  )}
                  {candidate.degree && (
                    <p className="text-sm md:text-base text-gray-600">{candidate.degree}</p>
                  )}
                  {candidate.election_time && (
                    <p className="text-xs md:text-sm text-gray-500 mt-1">
                      Saylov vaqti: {formatDateTime(candidate.election_time)}
                    </p>
                  )}
                </div>
              </div>

              {candidate.description && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-gray-700">
                  <p>{candidate.description}</p>
                </div>
              )}
            </>
          )}

          {/* Show grouped candidates header */}
          {hasAlternatives && (
            <div className="mb-6">
              <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">
                {candidate.which_position || 'Lavozim'}
              </h2>
              <p className="text-center text-gray-600 mb-4">
                Quyidagi nomzodlardan bittasini tanlang
              </p>
            </div>
          )}

          <div className="w-full mb-6">
            {timerStarted ? (
              <>
                <div className={`text-center mb-4 ${votingActive ? 'text-green-600' : 'text-gray-600'}`}>
                  <div className="text-5xl md:text-6xl font-bold mb-2">
                    {remainingSeconds}
                  </div>
                  <p className="text-sm md:text-base font-semibold">
                    {votingActive ? 'Ovoz berish davom etmoqda' : 'Bu kandidat uchun vaqt tugadi'}
                  </p>
                </div>
                {timer?.duration_sec ? (
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${votingActive ? 'bg-green-500' : 'bg-gray-400'}`}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                ) : null}
              </>
            ) : (
              <div className="text-center text-blue-600 font-semibold">
                Admin ovoz berishni boshlashini kuting
              </div>
            )}
          </div>

          {/* Voting Buttons */}
          {hasVoted ? (
            <div className="bg-green-100 border-2 border-green-500 rounded-xl p-6 md:p-8 text-center">
              <p className="text-xl md:text-3xl font-bold text-green-800 mb-2">
                ✓ Ovozingiz qabul qilindi!
              </p>
              <p className="text-green-700 text-sm md:text-base">
                Keyingi kandidatni kutib turing...
              </p>
            </div>
          ) : votingActive ? (
            hasAlternatives && relatedCandidates.length > 1 ? (
              // Grouped voting: select one candidate from the group
              <div className="relative pb-24">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {relatedCandidates.map((rc) => {
                    const isSelected = selectedCandidateId === rc.id;
                    return (
                      <button
                        key={rc.id}
                        onClick={() => setSelectedCandidateId(rc.id)}
                        className={`group relative p-5 rounded-xl border-2 transition-all duration-200 text-left ${
                          isSelected
                            ? 'border-green-500 bg-green-50 shadow-xl scale-105'
                            : 'border-gray-300 bg-white hover:border-green-400 hover:bg-green-50 hover:shadow-lg'
                        }`}
                      >
                        {isSelected && (
                          <div className="absolute -top-2 -right-2 bg-green-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-lg font-bold">
                            ✓
                          </div>
                        )}
                        <div className="flex flex-col items-center text-center gap-3">
                          {rc.image && (
                            <img
                              src={rc.image}
                              alt={rc.full_name}
                              className={`w-20 h-20 md:w-24 md:h-24 object-cover rounded-full border-4 transition-colors ${
                                isSelected
                                  ? 'border-green-500'
                                  : 'border-gray-200 group-hover:border-green-400'
                              }`}
                            />
                          )}
                          <div>
                            <p className="font-bold text-lg mb-1">{rc.full_name}</p>
                            {rc.degree && <p className="text-sm text-gray-600">{rc.degree}</p>}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
                <div className="mt-4 bg-yellow-50 border border-yellow-300 rounded-lg p-3">
                  <p className="text-center text-sm text-yellow-800 font-medium">
                    ⚠️ Tanlangan nomzod "Ha" ovoz oladi, qolganlari "Yo'q" ovoz oladi
                  </p>
                </div>

                {/* Floating Vote Button */}
                {selectedCandidateId && (
                  <div className="fixed bottom-0 left-0 right-0 bg-white border-t-4 border-green-500 shadow-2xl p-4 z-50">
                    <div className="max-w-4xl mx-auto">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex-1">
                          <p className="text-sm text-gray-600">Tanlangan nomzod:</p>
                          <p className="font-bold text-lg">
                            {relatedCandidates.find(rc => rc.id === selectedCandidateId)?.full_name}
                          </p>
                        </div>
                        <button
                          onClick={() => castVote('yes', selectedCandidateId)}
                          className="bg-green-600 text-white px-8 py-4 rounded-xl font-bold text-xl hover:bg-green-700 transition-colors shadow-lg flex items-center gap-2"
                        >
                          <span>✓</span>
                          <span>Ovoz berish</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              // Standard voting: Yes/No/Neutral buttons
              <div className="space-y-3 md:space-y-4">
                <button
                  onClick={() => castVote('yes')}
                  className="w-full bg-green-600 text-white py-4 md:py-6 rounded-xl font-bold text-lg md:text-2xl hover:bg-green-700 transition-colors shadow-lg active:scale-95"
                >
                  ✓ Ha
                </button>
                <button
                  onClick={() => castVote('no')}
                  className="w-full bg-red-600 text-white py-4 md:py-6 rounded-xl font-bold text-lg md:text-2xl hover:bg-red-700 transition-colors shadow-lg active:scale-95"
                >
                  ✗ Yo'q
                </button>
                <button
                  onClick={() => castVote('neutral')}
                  className="w-full bg-gray-600 text-white py-4 md:py-6 rounded-xl font-bold text-lg md:text-2xl hover:bg-gray-700 transition-colors shadow-lg active:scale-95"
                >
                  ○ Betaraf
                </button>
              </div>
            )
          ) : timerStarted ? (
            <div className="bg-yellow-100 border-2 border-yellow-400 rounded-xl p-6 md:p-8 text-center">
              <p className="text-xl md:text-2xl font-semibold text-yellow-800 mb-2">
                Vaqt tugadi
              </p>
              <p className="text-yellow-700 text-sm md:text-base">
                Admin keyingi kandidatni ishga tushirguncha kuting
              </p>
            </div>
          ) : (
            <div className="bg-blue-100 border-2 border-blue-400 rounded-xl p-6 md:p-8 text-center">
              <p className="text-xl md:text-2xl font-semibold text-blue-800 mb-2">
                Ovoz berish hali boshlanmadi
              </p>
              <p className="text-blue-700 text-sm md:text-base">
                Admin "Timer Start" tugmasini bosishini kuting
              </p>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border-2 border-blue-300 rounded-xl p-4 md:p-6">
          <p className="text-blue-800 text-center text-sm md:text-base">
            💡 Har bir kandidat uchun faqat bir marta ovoz berishingiz mumkin
          </p>
        </div>
      </div>
    </div>
  );
}
