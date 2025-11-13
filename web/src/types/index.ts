export interface Candidate {
  id: number;
  full_name: string;
  image?: string;
  birth_date?: string;
  degree?: string;
  which_position?: string;
  election_time?: string;
  description?: string;
  from_api: boolean;
  external_id?: number;
}

export enum EventStatus {
  PENDING = "pending",
  ACTIVE = "active",
  FINISHED = "finished",
  ARCHIVED = "archived"
}

export interface Event {
  id: number;
  name: string;
  link: string;
  duration_sec: number;
  status: EventStatus;
  start_time?: string;
  end_time?: string;
  candidates?: Candidate[];
  candidate_count?: number;
}

export interface VoteTally {
  candidate_id: number;
  full_name: string;
  image?: string;
  which_position?: string;
  election_time?: string | null;
  description?: string | null;
  votes: number;
  percent: number;
}

export interface VoteResults {
  yes: number;
  no: number;
  neutral: number;
  total: number;
}

export interface TimerState {
  running: boolean;
  remaining_ms: number;
  duration_sec: number;
  started_at?: string | null;
  ends_at?: string | null;
  ends_at_ts?: number | null;
}

export interface CurrentCandidate {
  candidate: Candidate | null;
  event_candidate_id?: number;
  index: number;
  total: number;
  timer?: TimerState;
  related_candidates?: Candidate[];
}

export interface GroupResult {
  candidate: Candidate;
  votes: VoteResults;
}

export interface DisplayState {
  type?: string;
  event_id?: number;
  candidate?: Candidate | null;
  current_candidate?: Candidate | null;
  related_candidates?: Candidate[];
  group_results?: GroupResult[];
  remaining_ms: number;
  vote_results?: VoteResults;
  timer_running?: boolean;
  timer?: TimerState;
  event_status?: EventStatus;
  event_completed?: boolean;
  final_results?: VoteTally[];
  total_votes?: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
