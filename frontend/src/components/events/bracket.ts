import type {
  EventMatchResponse, EventParticipantResponse, EventBracketGroup,
} from '@/types/events';

export interface ResolvedMatch {
  match: EventMatchResponse;
  slotAId: string | null;   // raw participant id for slot A
  slotBId: string | null;   // raw participant id for slot B
  slotAName: string | null;
  slotBName: string | null;
  isBye: boolean;       // exactly one slot filled
  isReady: boolean;     // both slots filled and not yet completed
  winnerName: string | null;
}

export interface BracketColumn {
  round: number;
  matches: ResolvedMatch[];
}

export interface BracketGroupView {
  group: EventBracketGroup;
  title: string;
  columns: BracketColumn[];
}

export interface BracketView {
  groups: BracketGroupView[];
  championId: string | null;
  championName: string | null;
}

const GROUP_TITLE: Record<EventBracketGroup, string> = {
  WINNERS: 'Winners Bracket',
  LOSERS: 'Losers Bracket',
  GRAND_FINAL: 'Grand Final',
};

const GROUP_ORDER: EventBracketGroup[] = ['WINNERS', 'LOSERS', 'GRAND_FINAL'];

function nameOf(map: Map<string, EventParticipantResponse>, id: string | null): string | null {
  if (!id) return null;
  return map.get(id)?.name ?? null;
}

export function buildBracket(
  matches: EventMatchResponse[],
  participants: EventParticipantResponse[],
): BracketView {
  const byId = new Map(participants.map((p) => [p.id, p]));
  const roundsByGroup = new Map<EventBracketGroup, Map<number, ResolvedMatch[]>>();
  for (const g of GROUP_ORDER) roundsByGroup.set(g, new Map());

  for (const m of matches) {
    const filled = [m.slot_a_id, m.slot_b_id].filter(Boolean).length;
    const resolved: ResolvedMatch = {
      match: m,
      slotAId: m.slot_a_id ?? null,
      slotBId: m.slot_b_id ?? null,
      slotAName: nameOf(byId, m.slot_a_id),
      slotBName: nameOf(byId, m.slot_b_id),
      isBye: filled === 1,
      isReady: filled === 2 && m.status === 'PENDING',
      winnerName: m.winner_id ? nameOf(byId, m.winner_id) : null,
    };
    const rounds = roundsByGroup.get(m.bracket_group)!;
    if (!rounds.has(m.round)) rounds.set(m.round, []);
    rounds.get(m.round)!.push(resolved);
  }

  const groups: BracketGroupView[] = [];
  for (const g of GROUP_ORDER) {
    const rounds = roundsByGroup.get(g)!;
    if (rounds.size === 0) continue;
    const columns = [...rounds.keys()]
      .sort((a, b) => a - b)
      .map((round) => ({ round, matches: rounds.get(round)! }));
    groups.push({ group: g, title: GROUP_TITLE[g], columns });
  }

  const champion = matches.find((m) => m.next_match_id === null && m.winner_id);
  const championId = champion?.winner_id ?? null;
  const championName = championId ? nameOf(byId, championId) : null;

  return { groups, championId, championName };
}
