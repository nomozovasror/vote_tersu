import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import api, { WS_BASE_URL } from '../utils/api';
import { Event, VoteTally } from '../types';

export default function VotePage() {
  const { link } = useParams<{ link: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [tally, setTally] = useState<VoteTally[]>([]);
  const [hasVoted, setHasVoted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const nonce = useRef(crypto.randomUUID());

  useEffect(() => {
    fetchEvent();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [link]);

  const fetchEvent = async () => {
    try {
      const response = await api.get(`/events/by-link/${link}`);
      setEvent(response.data);
    } catch (error) {
      setError('Event not found');
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/vote/${link}`);

    ws.onopen = () => {
      console.log('Connected to voting WebSocket');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'initial_tally' || data.type === 'tally_update') {
        setTally(data.data);
      } else if (data.type === 'vote_confirmed') {
        setHasVoted(true);
      } else if (data.type === 'error') {
        alert(data.message);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };

    wsRef.current = ws;
  };

  const castVote = (candidateId: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'cast_vote',
        candidate_id: candidateId,
        nonce: nonce.current
      }));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-600">{error || 'Event not found'}</div>
      </div>
    );
  }

  if (event.status !== 'active') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-yellow-600">
          This event is not currently active
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <h1 className="text-4xl font-bold text-center mb-2">{event.name}</h1>
          <p className="text-center text-gray-600">
            {hasVoted ? 'Thank you for voting!' : 'Select your candidate'}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {event.candidates?.map((candidate) => {
            const candidateTally = tally.find(t => t.candidate_id === candidate.id);
            return (
              <div
                key={candidate.id}
                className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
              >
                {candidate.image && (
                  <img
                    src={candidate.image}
                    alt={candidate.full_name}
                    className="w-full h-64 object-cover"
                  />
                )}
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2">{candidate.full_name}</h3>
                  {candidate.which_position && (
                    <p className="text-gray-600 mb-2">{candidate.which_position}</p>
                  )}
                  {candidate.degree && (
                    <p className="text-gray-500 text-sm mb-4">{candidate.degree}</p>
                  )}

                  {candidateTally && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm mb-1">
                        <span>Votes: {candidateTally.votes}</span>
                        <span>{candidateTally.percent.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${candidateTally.percent}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <button
                    onClick={() => castVote(candidate.id)}
                    disabled={hasVoted}
                    className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                      hasVoted
                        ? 'bg-gray-300 cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {hasVoted ? 'Voted' : 'Vote'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Live Results */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h2 className="text-2xl font-bold mb-6">Live Results</h2>
          <div className="space-y-4">
            {tally.map((item, index) => (
              <div key={item.candidate_id}>
                <div className="flex justify-between mb-2">
                  <span className="font-semibold">
                    {index + 1}. {item.full_name}
                  </span>
                  <span className="text-gray-600">
                    {item.votes} votes ({item.percent.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-4 rounded-full transition-all"
                    style={{ width: `${item.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
