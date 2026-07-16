import { describe, it, expect } from 'vitest';
import { buildBracket } from './bracket';
import type { EventMatchResponse, EventParticipantResponse } from '@/types/events';

const P = (id: string, name: string): EventParticipantResponse => ({
  id, event_id: 'e1', member_id: null, name, seat_id: null, bracket_position: 0, eliminated: false,
});

function M(p: Partial<EventMatchResponse>): EventMatchResponse {
  return {
    id: p.id ?? 'm', event_id: 'e1', bracket_group: 'WINNERS', round: 1,
    slot_a_id: null, slot_b_id: null, winner_id: null, status: 'PENDING',
    next_match_id: null, next_loser_match_id: null, ...p,
  } as EventMatchResponse;
}

describe('buildBracket', () => {
  it('groups single-elimination rounds and finds the champion', () => {
    const participants = [P('pA', 'Alice'), P('pB', 'Bob'), P('pC', 'Cara'), P('pD', 'Dan')];
    const matches = [
      M({ id: 'm1', round: 1, slot_a_id: 'pA', slot_b_id: 'pB', winner_id: 'pA', status: 'COMPLETED', next_match_id: 'm3' }),
      M({ id: 'm2', round: 1, slot_a_id: 'pC', slot_b_id: 'pD', winner_id: 'pC', status: 'COMPLETED', next_match_id: 'm3' }),
      M({ id: 'm3', round: 2, slot_a_id: 'pA', slot_b_id: 'pC', winner_id: 'pA', status: 'COMPLETED', next_match_id: null }),
    ];
    const view = buildBracket(matches, participants);
    expect(view.groups).toHaveLength(1);
    expect(view.groups[0].group).toBe('WINNERS');
    expect(view.groups[0].columns.map((c) => c.matches.length)).toEqual([2, 1]);
    expect(view.championId).toBe('pA');
    expect(view.championName).toBe('Alice');
  });

  it('marks a one-slot match as a bye and a two-slot pending match as ready', () => {
    const participants = [P('pA', 'Alice'), P('pB', 'Bob')];
    const matches = [
      M({ id: 'm1', round: 1, slot_a_id: 'pA', slot_b_id: null }),
      M({ id: 'm2', round: 1, slot_a_id: 'pA', slot_b_id: 'pB' }),
    ];
    const view = buildBracket(matches, participants);
    const [m1, m2] = view.groups[0].columns[0].matches;
    expect(m1.isBye).toBe(true);
    expect(m1.isReady).toBe(false);
    expect(m2.isBye).toBe(false);
    expect(m2.isReady).toBe(true);
  });

  it('separates winners, losers, and grand final groups for double elimination', () => {
    const participants = [P('pA', 'Alice'), P('pB', 'Bob')];
    const matches = [
      M({ id: 'w1', bracket_group: 'WINNERS', round: 1, slot_a_id: 'pA', slot_b_id: 'pB', winner_id: 'pA', status: 'COMPLETED', next_match_id: 'gf' }),
      M({ id: 'l1', bracket_group: 'LOSERS', round: 1, slot_a_id: 'pB', slot_b_id: null }),
      M({ id: 'gf', bracket_group: 'GRAND_FINAL', round: 1, slot_a_id: 'pA', slot_b_id: 'pB', winner_id: 'pA', status: 'COMPLETED', next_match_id: null }),
    ];
    const view = buildBracket(matches, participants);
    expect(view.groups.map((g) => g.group)).toEqual(['WINNERS', 'LOSERS', 'GRAND_FINAL']);
    expect(view.groups[2].title).toBe('Grand Final');
    expect(view.championId).toBe('pA');
  });
});
