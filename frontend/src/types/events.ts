// Mirrors backend/schemas/event.py. Monetary fields are integers in paise.
export type EventBracketType = 'SINGLE_ELIMINATION' | 'DOUBLE_ELIMINATION';
export type EventStatus = 'UPCOMING' | 'ACTIVE' | 'COMPLETED';
export type EventBracketGroup = 'WINNERS' | 'LOSERS' | 'GRAND_FINAL';
export type EventMatchStatus = 'PENDING' | 'COMPLETED';

export interface EventResponse {
  id: string;
  name: string;
  game_title: string;
  event_date: string; // ISO datetime
  entry_fee_paise: number;
  prize_pool_paise: number;
  bracket_type: EventBracketType;
  status: EventStatus;
}

export interface EventParticipantResponse {
  id: string;
  event_id: string;
  member_id: string | null;
  name: string;
  seat_id: string | null;
  bracket_position: number | null;
  eliminated: boolean;
}

export interface EventMatchResponse {
  id: string;
  event_id: string;
  bracket_group: EventBracketGroup;
  round: number;
  slot_a_id: string | null;
  slot_b_id: string | null;
  winner_id: string | null;
  status: EventMatchStatus;
  next_match_id: string | null;
  next_loser_match_id: string | null;
}

export interface EventSummaryResponse {
  event: EventResponse;
  participant_count: number;
  participants: EventParticipantResponse[];
  match_count: number;
  completed_match_count: number;
  prize_pool_paise: number;
  entry_fee_paise: number;
  entry_fee_revenue_paise: number;
  champion_participant_id: string | null;
  is_complete: boolean;
  matches: EventMatchResponse[];
}

export interface EventCreate {
  name: string;
  game_title: string;
  event_date: string; // ISO datetime
  entry_fee_paise?: number;
  prize_pool_paise?: number;
  bracket_type?: EventBracketType;
  status?: EventStatus;
}

export interface EventRegisterRequest {
  member_id?: string | null;
  name?: string | null;
  seat_id?: string | null;
}

export interface EventMatchResultRequest {
  match_id: string;
  winner_id: string;
}
