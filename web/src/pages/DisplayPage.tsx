import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { WS_BASE_URL } from '../utils/api';
import { DisplayState, VoteResults, VoteTally } from '../types';

export default function DisplayPage() {
  const { link } = useParams<{ link: string }>();
  const [displayState, setDisplayState] = useState<DisplayState | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const countdownTarget = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastBeepSecond = useRef<number>(-1);
  const finalResults = (displayState?.final_results || []) as VoteTally[];
  const finalTotalVotes = displayState?.total_votes || 0;
  const eventCompleted = displayState?.event_completed ?? false;

  // Initialize audio context
  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Play beep sound
  const playBeep = (frequency: number = 800, duration: number = 100) => {
    if (!audioContextRef.current) return;

    const ctx = audioContextRef.current;
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration / 1000);

    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + duration / 1000);
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [link]);

  useEffect(() => {
    const timer = displayState?.timer;

    if (!timer) {
      countdownTarget.current = null;
      setRemainingSeconds(0);
      return;
    }

    const remainingMs = timer.remaining_ms ?? 0;
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
        : displayState?.timer_running && remainingMs > 0
        ? nowMs + remainingMs
        : null;

    countdownTarget.current = targetMs;

    if (displayState?.timer_running && targetMs) {
      setRemainingSeconds(Math.max(0, Math.ceil((targetMs - nowMs) / 1000)));
    } else if (timer.started_at) {
      setRemainingSeconds(Math.max(0, Math.ceil(remainingMs / 1000)));
    } else {
      setRemainingSeconds(0);
    }
  }, [
    displayState?.timer_running,
    displayState?.timer?.started_at,
    displayState?.timer?.ends_at,
    displayState?.timer?.ends_at_ts,
    displayState?.timer?.remaining_ms,
  ]);

  useEffect(() => {
    if (!displayState?.timer_running || !countdownTarget.current) {
      lastBeepSecond.current = -1;
      return;
    }

    const tick = () => {
      if (!countdownTarget.current) {
        return;
      }
      const remaining = countdownTarget.current - Date.now();
      if (remaining <= 0) {
        setRemainingSeconds(0);
        countdownTarget.current = null;
        lastBeepSecond.current = -1;
      } else {
        const currentSecond = Math.ceil(remaining / 1000);
        setRemainingSeconds(currentSecond);

        // Play beep sound on each second change
        if (currentSecond !== lastBeepSecond.current && currentSecond > 0) {
          lastBeepSecond.current = currentSecond;

          // Different beep patterns based on remaining time
          if (currentSecond <= 5) {
            // High pitch rapid beep for last 5 seconds
            playBeep(1200, 150);
          } else if (currentSecond <= 10) {
            // Medium pitch for 6-10 seconds
            playBeep(1000, 120);
          } else {
            // Normal beep for rest
            playBeep(800, 100);
          }
        }
      }
    };

    tick();
    const interval = window.setInterval(tick, 250);
    return () => {
      window.clearInterval(interval);
      lastBeepSecond.current = -1;
    };
  }, [displayState?.timer_running, displayState?.timer?.started_at, displayState?.timer?.ends_at_ts]);

  const connectWebSocket = () => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/display/${link}`);

    ws.onopen = () => {
      console.log('Connected to display WebSocket');
      ws.send('update');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'display_update') {
        setDisplayState(data);
      } else if (data.type === 'candidate_changed') {
        // Request fresh update when candidate changes
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('update');
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;

    // Keep alive and request updates
    const keepAlive = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('update');
      }
    }, 1000);

    return () => clearInterval(keepAlive);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const candidate = displayState?.candidate || displayState?.current_candidate;
  const groupResults = displayState?.group_results || [];
  const voteResults = displayState?.vote_results || { yes: 0, no: 0, neutral: 0, total: 0 };
  const timerRunning = displayState?.timer_running ?? false;
  const timer = displayState?.timer;
  const isGrouped = groupResults.length > 1;
  const timerStarted = !!timer?.started_at;
  const durationSec = timer?.duration_sec ?? 0;
  const waitingMode = !timerRunning && !timerStarted;
  const showResults = timerStarted && (!timerRunning || remainingSeconds <= 0);
  const progressPercent = durationSec > 0
    ? Math.max(0, Math.min(100, (remainingSeconds / durationSec) * 100))
    : 0;

  // Debug logging
  console.log('[DisplayPage] groupResults:', groupResults);
  console.log('[DisplayPage] showResults:', showResults);
  console.log('[DisplayPage] isGrouped:', isGrouped);

  if (eventCompleted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 text-white relative">
        <button
          onClick={toggleFullscreen}
          className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg backdrop-blur z-10"
        >
          {isFullscreen ? 'Chiqish' : 'Fullscreen'}
        </button>

        <div className="container mx-auto px-6 md:px-10 py-12 min-h-screen flex items-center">
          <div className="w-full bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-6 md:p-12">
            <h1 className="text-4xl md:text-6xl font-bold text-center mb-6">Yakuniy natijalar</h1>
            <p className="text-center text-lg md:text-2xl text-gray-200 mb-10">
              Jami ovozlar: <span className="font-semibold text-white">{finalTotalVotes}</span>
            </p>

            {finalResults.length > 0 ? (
              <div className="space-y-4">
                {finalResults.map((result, index) => (
                  <div
                    key={result.candidate_id}
                    className="flex items-center justify-between bg-white/15 border border-white/20 rounded-2xl px-5 py-4 hover:bg-white/20 transition-all"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl md:text-3xl font-bold text-yellow-300 min-w-[3rem] text-center">{index + 1}</span>
                      {result.image && (
                        <img
                          src={result.image}
                          alt={result.full_name}
                          className="w-16 h-16 md:w-20 md:h-20 rounded-full object-cover border-4 border-yellow-300/50 shadow-lg"
                        />
                      )}
                      <div>
                        <p className="text-xl md:text-2xl font-semibold">{result.full_name}</p>
                        {result.which_position && (
                          <p className="text-sm md:text-base text-blue-300 font-medium">{result.which_position}</p>
                        )}
                        {result.election_time && (
                          <p className="text-sm md:text-base text-gray-300">{result.election_time}</p>
                        )}
                        <p className="text-base md:text-lg text-green-300 mt-1 font-semibold">{result.percent.toFixed(1)}%</p>
                        {result.description && (
                          <p className="text-xs md:text-sm text-gray-300 mt-1 line-clamp-2">{result.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-xl md:text-3xl font-bold text-white bg-gradient-to-r from-green-500 to-blue-500 px-6 py-3 rounded-xl shadow-lg">
                      {result.votes}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-200">Natijalar mavjud emas.</div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-6xl font-bold mb-4">Kutilmoqda...</h1>
          <p className="text-2xl text-gray-400">Admin tomonidan ovoz berish boshlanadi</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 text-white relative">
      {/* Fullscreen Toggle Button */}
      <button
        onClick={toggleFullscreen}
        className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg backdrop-blur z-10"
      >
        {isFullscreen ? 'Chiqish' : 'Fullscreen'}
      </button>

      <div className="container mx-auto px-8 py-8 h-screen flex items-center">
        {isGrouped ? (
          /* Grouped Candidates Layout */
          <div className="w-full h-full flex flex-col">
            <div className="text-center mb-6">
              <h1 className="text-5xl font-bold mb-2">
                {candidate?.which_position || 'Lavozim'}
              </h1>
              <p className="text-2xl text-gray-300">Nomzodlar</p>
            </div>

            <div className={`grid ${groupResults.length === 2 ? 'grid-cols-2' : groupResults.length === 3 ? 'grid-cols-3' : 'grid-cols-2'} gap-6 flex-1 overflow-hidden`}>
              {groupResults.map((gr) => (
                <div key={gr.candidate.id} className="bg-white/10 backdrop-blur rounded-3xl p-5 border-2 border-white/20 flex flex-col overflow-hidden">
                  {/* Candidate Info Section - Fixed Height */}
                  <div className="flex-shrink-0 mb-4">
                    <div className="flex items-start gap-4">
                      {gr.candidate.image && (
                        <img
                          src={gr.candidate.image}
                          alt={gr.candidate.full_name}
                          className="w-24 h-24 object-cover rounded-2xl shadow-xl border-4 border-white/20 flex-shrink-0"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xl font-bold mb-1 truncate">{gr.candidate.full_name}</h3>
                        {gr.candidate.which_position && (
                          <p className="text-base text-blue-300 mb-1 truncate">{gr.candidate.which_position}</p>
                        )}
                        {gr.candidate.degree && (
                          <p className="text-sm text-gray-300 truncate">{gr.candidate.degree}</p>
                        )}
                        {gr.candidate.election_time && (
                          <p className="text-xs text-gray-400 mt-1 truncate">
                            Vaqt: {gr.candidate.election_time}
                          </p>
                        )}
                      </div>
                    </div>
                    {gr.candidate.description && (
                      <div className="text-xs text-gray-300 bg-white/5 rounded-lg px-3 py-2 mt-2 max-h-12 overflow-y-auto line-clamp-2">
                        {gr.candidate.description}
                      </div>
                    )}
                  </div>

                  {/* Timer or Results for this candidate - Horizontal Layout */}
                  <div className="flex-1 flex items-center justify-center min-h-0">
                    {waitingMode ? (
                      <div className="text-center py-2">
                        <p className="text-base text-gray-400">Kutilmoqda...</p>
                      </div>
                    ) : timerRunning && remainingSeconds > 0 ? (
                      /* Show timer while voting is active */
                      <div className="text-center py-4">
                        <div className="text-7xl md:text-8xl font-bold mb-2">{remainingSeconds}</div>
                        <p className="text-lg md:text-xl text-gray-300">soniya</p>
                      </div>
                    ) : gr.votes ? (
                      /* Show results when timer has ended (even if no votes yet) */
                      <div className="w-full flex items-center gap-4 px-4">
                        <div className="relative w-32 h-32 md:w-40 md:h-40 flex-shrink-0">
                          <PieChart results={gr.votes} />
                        </div>
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center justify-between bg-green-600/30 px-4 py-2.5 rounded-lg">
                            <span className="text-base md:text-lg font-semibold">Ha</span>
                            <span className="text-base md:text-lg font-bold">
                              {gr.votes.yes} ({gr.votes.total > 0 ? ((gr.votes.yes / gr.votes.total) * 100).toFixed(1) : 0}%)
                            </span>
                          </div>
                          <div className="flex items-center justify-between bg-red-600/30 px-4 py-2.5 rounded-lg">
                            <span className="text-base md:text-lg font-semibold">Yo'q</span>
                            <span className="text-base md:text-lg font-bold">
                              {gr.votes.no} ({gr.votes.total > 0 ? ((gr.votes.no / gr.votes.total) * 100).toFixed(1) : 0}%)
                            </span>
                          </div>
                          {gr.votes.neutral > 0 && (
                            <div className="flex items-center justify-between bg-gray-600/30 px-4 py-2.5 rounded-lg">
                              <span className="text-base md:text-lg font-semibold">Betaraf</span>
                              <span className="text-base md:text-lg font-bold">
                                {gr.votes.neutral} ({gr.votes.total > 0 ? ((gr.votes.neutral / gr.votes.total) * 100).toFixed(1) : 0}%)
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      /* No votes data available */
                      <div className="text-center py-2">
                        <p className="text-base text-gray-400">Ovozlar kutilmoqda...</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Standard Single Candidate Layout */
          <div className="grid grid-cols-2 gap-12 w-full">
            {/* Left Side - Candidate Info */}
            <div className="flex flex-col justify-center">
              {candidate?.image && (
                <img
                  src={candidate.image}
                  alt={candidate.full_name}
                  className="w-96 h-96 object-cover rounded-3xl shadow-2xl border-4 border-white/20 mb-8 mx-auto"
                />
              )}
              <div className="text-center">
                <h2 className="text-5xl font-bold mb-4 leading-tight">
                  {candidate?.full_name}
                </h2>
                {candidate?.which_position && (
                  <p className="text-3xl text-blue-300 mb-3">{candidate.which_position}</p>
                )}
                {candidate?.degree && (
                  <p className="text-2xl text-gray-300">{candidate.degree}</p>
                )}
                {candidate?.election_time && (
                  <p className="text-xl text-gray-300 mt-3">
                    Saylov vaqti: {candidate.election_time}
                  </p>
                )}
              </div>
              {candidate?.description && (
                <div className="mt-6 text-lg text-gray-200 bg-white/10 border border-white/20 rounded-2xl px-6 py-4">
                  {candidate.description}
                </div>
              )}
            </div>

            {/* Right Side - Timer or Results */}
            <div className="flex flex-col justify-center items-center">
              {waitingMode ? (
                <div className="text-center text-gray-300">
                  <div className="text-7xl font-bold mb-6">Ovoz berish kutilmoqda</div>
                  <p className="text-3xl text-gray-400">Admin boshlashini kuting</p>
                </div>
              ) : !showResults ? (
                /* Timer */
                <div className="text-center">
                  <div className="text-[15rem] font-bold leading-none mb-8">
                    {remainingSeconds}
                  </div>
                  <div className="text-4xl text-gray-300 mb-8">soniya qoldi</div>

                  {/* Progress Bar */}
                  <div className="w-full max-w-2xl">
                    <div className="w-full bg-gray-700 rounded-full h-6">
                      <div
                        className="bg-gradient-to-r from-green-400 to-blue-500 h-6 rounded-full transition-all duration-1000"
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-12 text-5xl font-semibold text-yellow-300 animate-pulse">
                    OVOZ BERING!
                  </div>
                </div>
              ) : (
                /* Pie Chart Results */
                <div className="w-full max-w-2xl">
                  <h3 className="text-5xl font-bold mb-12 text-center">Natijalar</h3>

                  {/* Simple Pie Chart using CSS */}
                  <div className="relative w-96 h-96 mx-auto mb-12">
                    <PieChart results={voteResults} />
                  </div>

                  {/* Results Breakdown */}
                  <div className="space-y-6">
                    <div className="flex items-center justify-between bg-green-600/30 p-6 rounded-xl">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-green-500 rounded"></div>
                        <span className="text-3xl font-semibold">Ha</span>
                      </div>
                      <span className="text-4xl font-bold">
                        {voteResults.yes} ({voteResults.total > 0 ?
                          ((voteResults.yes / voteResults.total) * 100).toFixed(1) : 0}%)
                      </span>
                    </div>

                    <div className="flex items-center justify-between bg-red-600/30 p-6 rounded-xl">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-red-500 rounded"></div>
                        <span className="text-3xl font-semibold">Yo'q</span>
                      </div>
                      <span className="text-4xl font-bold">
                        {voteResults.no} ({voteResults.total > 0 ?
                          ((voteResults.no / voteResults.total) * 100).toFixed(1) : 0}%)
                      </span>
                    </div>

                    <div className="flex items-center justify-between bg-gray-600/30 p-6 rounded-xl">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-gray-500 rounded"></div>
                        <span className="text-3xl font-semibold">Betaraf</span>
                      </div>
                      <span className="text-4xl font-bold">
                        {voteResults.neutral} ({voteResults.total > 0 ?
                          ((voteResults.neutral / voteResults.total) * 100).toFixed(1) : 0}%)
                      </span>
                    </div>

                    <div className="text-center mt-8 text-3xl font-bold text-yellow-300">
                      Jami: {voteResults.total} ovoz
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Simple Pie Chart Component
function PieChart({ results }: { results: VoteResults }) {
  const total = results.total || 1;
  const yesPercent = (results.yes / total) * 100;
  const noPercent = (results.no / total) * 100;

  // Create conic gradient
  const gradient = `conic-gradient(
    #10b981 0deg ${yesPercent * 3.6}deg,
    #ef4444 ${yesPercent * 3.6}deg ${(yesPercent + noPercent) * 3.6}deg,
    #6b7280 ${(yesPercent + noPercent) * 3.6}deg 360deg
  )`;

  return (
    <div
      className="w-full h-full rounded-full shadow-2xl"
      style={{ background: gradient }}
    >
      <div className="w-full h-full flex items-center justify-center">
        <div className="bg-gray-900 w-32 h-32 rounded-full flex items-center justify-center">
          <span className="text-4xl font-bold">{total}</span>
        </div>
      </div>
    </div>
  );
}
