-- Game model for the Jin Chan Chan replay page (schema v3).
-- Pure, computable definitions. No Mathlib, no axioms.
-- Every check is a `Bool` function over the trace data so that
-- `Proofs.lean` can discharge it with `native_decide`.
--
-- Two layers:
-- Layer 1 (market game): players, rounds, HP/gold, cards. Rules are
-- VERSIONED parameters, not constants: each move is checked against
-- the rule version in effect at its date (never today's rule applied
-- to a past round). Each move records its rule version (ROUND_RV).
-- Layer 2 (meta-game / rule table): rule-makers enact rule versions;
-- companies lobby. C10/C11/C12 check the meta-game.
--
-- Dates are YYYYMMDD naturals. `effectiveTo == 0` means "no end".
-- Rule `targets == []` means "applies to all players" (a global rule);
-- a non-empty list is a player-specific overlay.
namespace Jjc

/-- One per-player action in one round. -/
structure Move where
  season : Nat
  roundIdx : Nat
  player : Nat
  hpDelta : Int
  goldDelta : Int
  actionKind : Nat
  date : Nat
  hpStart : Int
  goldStart : Int
  rulesVersion : Nat
  liability : Bool
  deriving DecidableEq, Repr, Inhabited

/-- Season boundary values for one (season, player). -/
structure SeasonState where
  season : Nat
  player : Nat
  hpStart : Int
  goldStart : Int
  hpEnd : Int
  goldEnd : Int
  borrowed : Int
  penalty : Int
  deriving DecidableEq, Repr, Inhabited

/-- One displayed ranking row. -/
structure Ranking where
  season : Nat
  player : Nat
  rank : Nat
  hpEnd : Int
  goldEnd : Int
  deriving DecidableEq, Repr, Inhabited

/-- One season: its round count, its recorded move total, and its
    active players. `moves` is the converter-recorded move total for
    the season (added 2026-11-24 for the monthly structure, where a
    round holds a variable number of moves and the old
    rounds * players equality no longer holds). -/
structure SeasonInfo where
  season : Nat
  rounds : Nat
  moves : Nat
  activePlayers : List Nat
  deriving DecidableEq, Repr, Inhabited

/-- One key card held by one player. -/
structure Holding where
  player : Nat
  card : String
  cost : Nat
  stars : Nat
  deriving DecidableEq, Repr, Inhabited

/-- One key card with its holders and earliest allowed date. -/
structure KeyCard where
  card : String
  cost : Nat
  holders : List Nat
  shared : Bool
  minDate : Nat
  deriving DecidableEq, Repr, Inhabited

/-- Anthropic IPO staged numbers, in millions of USD. -/
structure IpoFacts where
  baseUsdM : Nat
  greenshoeTotalUsdM : Nat
  privateUsdM : Nat
  basePlusPrivateUsdM : Nat
  combinedUsdM : Nat
  netUsdM : Nat
  deriving DecidableEq, Repr, Inhabited

/-- NVDA drop figures, prices in cents, drops in tenths of a percent. -/
structure NvdaFacts where
  closeHighCents : Nat
  closeDropTenthsPct : Nat
  intradayHighCents : Nat
  intradayDropTenthsPct : Nat
  lowCents : Nat
  deriving DecidableEq, Repr, Inhabited

/-- One versioned rule. `id` identifies the rule line; `version`
    distinguishes successive versions of the same line. -/
structure RuleVersion where
  id : Nat
  version : Nat
  effectiveFrom : Nat
  effectiveTo : Nat
  hpCap : Int
  hpFloor : Int
  penaltyNumer : Nat
  penaltyDenom : Nat
  penaltyAppliesToHp : Bool
  bannedKinds : List Nat
  unavailableCards : List String
  targets : List Nat
  deriving DecidableEq, Repr, Inhabited

/-- One rule-maker (layer 2 player). kind: 0 government, 1 agency,
    2 legislature, 3 state, 4 bloc, 5 company. layer1Role: 0 referee,
    1 player. layer2Role: 0 rulemaker, 1 lobbyist, 2 observer. -/
structure MetaPlayer where
  id : Nat
  kind : Nat
  layer1Role : Nat
  layer2Role : Nat
  deriving DecidableEq, Repr, Inhabited

/-- One rule action at the rule table. action: 0 enact, 1 amend,
    2 rescind. statedGoal: 0 national_security, 1 votes,
    2 industrial_advantage, 3 public_safety, 4 other. -/
structure RuleAction where
  ruleId : Nat
  version : Nat
  actor : Nat
  action : Nat
  effectiveFrom : Nat
  effectiveTo : Nat
  issuedBy : String
  docNumber : String
  statedGoal : Nat
  triggerEvent : String
  deriving DecidableEq, Repr, Inhabited

/-- One entry of the political record (the patch note's source). -/
structure PoliticalRecord where
  docNumber : String
  issuingBody : String
  effectiveDate : Nat
  title : String
  deriving DecidableEq, Repr, Inhabited

/-- A reference inside a trigger link: either one move (isMove) or
    one dated event (eventId + date). -/
structure TriggerRef where
  isMove : Bool
  season : Nat
  player : Nat
  roundIdx : Nat
  eventId : String
  date : Nat
  deriving DecidableEq, Repr, Inhabited

/-- One reflexive loop: observe -> rule -> react -> observe again. -/
structure TriggerLink where
  id : Nat
  observe : TriggerRef
  ruleAction : Nat
  react : TriggerRef
  hasAgain : Bool
  observeAgain : TriggerRef
  deriving DecidableEq, Repr, Inhabited

/-- One lobbying action by a layer-1 company. position: 0 support,
    1 oppose, 2 draft. -/
structure LobbyAction where
  id : Nat
  actor : Nat
  targetRule : Nat
  position : Nat
  deriving DecidableEq, Repr, Inhabited

/-- Distinct elements (first occurrence kept), core Lean has no
    `List.eraseDuplicates` in 4.36. -/
def distinct {α} [BEq α] (xs : List α) : List α :=
  xs.foldr (fun x acc => if acc.contains x then acc else x :: acc) []

/-- Is this rule version in effect on `date`? -/
def ruleInEffect (r : RuleVersion) (date : Nat) : Bool :=
  decide (r.effectiveFrom ≤ date) &&
    (r.effectiveTo == 0 || decide (date < r.effectiveTo))

/-- The global rule in effect on `date`: latest effectiveFrom wins. -/
def baseRuleAt (rules : List RuleVersion) (date : Nat)
    : Option RuleVersion :=
  (rules.filter fun r => r.targets.isEmpty && ruleInEffect r date).foldl
    (fun acc r => match acc with
      | none => some r
      | some y => if r.effectiveFrom > y.effectiveFrom then some r
                  else some y)
    none

/-- Player-specific overlay rules in effect on `date` for `player`. -/
def overlaysAt (rules : List RuleVersion) (date : Nat) (player : Nat)
    : List RuleVersion :=
  rules.filter fun r =>
    !r.targets.isEmpty && ruleInEffect r date && r.targets.contains player

/-- HP clamp under one rule version. -/
def capHp (r : RuleVersion) (x : Int) : Int :=
  min (max x r.hpFloor) r.hpCap

/-- Moves of one (season, player), in trace order. -/
def movesOf (ms : List Move) (s p : Nat) : List Move :=
  ms.filter fun m => m.season == s && m.player == p

/-- Non-decreasing round indices (a player may act several times in
    one round; the order within the round is trace order). Monthly
    structure (2026-11-24): the old strictly-increasing requirement
    assumed one move per player per round, which the monthly rounds
    (up to 117 moves in one round) do not satisfy. -/
def nonDecreasing : List Nat → Bool
  | [] => true
  | [_] => true
  | a :: b :: rest => decide (a ≤ b) && nonDecreasing (b :: rest)

/-- End of the round span `[date, spanEnd]` for one move. `spans` is
    a list of `(season, roundIdx, spanEnd)` from `rules/round-spans.json`
    (emitted into `Trace.lean` as `traceRoundSpans`). A round without an
    entry has spanEnd = its move date (no span). The stored end only
    extends the window forward: an end earlier than the move date
    cannot shrink it (mirrors `check.py: round_span_end`). -/
def spanEndFor (spans : List (Nat × Nat × Nat)) (season roundIdx date : Nat)
    : Nat :=
  match spans.find? fun sp => sp.1 == season && sp.2.1 == roundIdx with
  | none => date
  | some (_, _, e) => max date e

/-- True if the rule's window `[effectiveFrom, effectiveTo)` overlaps
    the closed span `[start, spanEnd]`. `effectiveTo == 0` means
    open-ended (mirrors `check.py: rule_window_overlaps`). -/
def ruleWindowOverlaps (r : RuleVersion) (start spanEnd : Nat) : Bool :=
  decide (r.effectiveFrom ≤ spanEnd) &&
    (r.effectiveTo == 0 || decide (start < r.effectiveTo))

/-- A move's recorded rule version is accepted iff it is the base
    (global) rule in effect at the move's date, or a base rule whose
    effective window overlaps the round span `[date, spanEnd]`
    (decision 2026-11-21, Gu approved). The span case covers a round
    whose true date range crosses a rule-change day, e.g. S5 round
    2026-11 (2026-11-01–21): its moves record RV-2026.2, whose window
    `[20261119, ∞)` overlaps the span at 20261119, although the base
    rule on the earliest day 20261118 is RV-2026.1. Player-specific
    overlays never qualify. Ban and date checks still use the move
    date only; this changes ROUND_RV acceptance only. -/
def ruleVersionAccepted (rules : List RuleVersion)
    (spans : List (Nat × Nat × Nat)) (m : Move) : Bool :=
  match baseRuleAt rules m.date with
  | none => false
  | some base =>
    m.rulesVersion == base.id ||
    rules.any fun r =>
      r.targets.isEmpty && r.id == m.rulesVersion &&
      ruleWindowOverlaps r m.date
        (spanEndFor spans m.season m.roundIdx m.date)

/-- Fold one group's chain under the rule version in effect at each
    move's date. Returns (ok, hpAfterLast, goldAfterLast).
    Each move must record an accepted rule version (ROUND_RV, see
    `ruleVersionAccepted`), continue the chain, keep HP inside the
    version's cap, keep gold >= 0 unless the move is flagged as
    liability, and use no action kind banned by the version in
    effect. -/
def chainFold (rules : List RuleVersion) (spans : List (Nat × Nat × Nat))
    (hp gold : Int)
    : List Move → Bool × Int × Int
  | [] => (true, hp, gold)
  | m :: rest =>
    match baseRuleAt rules m.date with
    | none => (false, hp, gold)
    | some base =>
      let banned := base.bannedKinds.any fun k => k == m.actionKind
      let bannedOv := (overlaysAt rules m.date m.player).any fun ov =>
        ov.bannedKinds.any fun k => k == m.actionKind
      if ruleVersionAccepted rules spans m && m.hpStart == hp &&
         m.goldStart == gold &&
         base.hpFloor ≤ m.hpStart && m.hpStart ≤ base.hpCap &&
         (0 ≤ gold + m.goldDelta || m.liability) &&
         !banned && !bannedOv then
        chainFold rules spans (capHp base (m.hpStart + m.hpDelta))
          (gold + m.goldDelta) rest
      else
        (false, hp, gold)

/-- The rule version in effect at the END of a season for one player:
    the base rule in effect at the last move's date. -/
def endRule (rules : List RuleVersion) (ms : List Move) (s p : Nat)
    : Option RuleVersion :=
  match movesOf ms s p with
  | [] => none
  | group =>
    match group.getLast? with
    | none => none
    | some m => baseRuleAt rules m.date

/-- C2/C3/C9 for one (season, player): chain + season end + ranking
    match. The leverage penalty is `borrowed * numer / denom`
    (floor for non-negative borrowed), applied to HP when the
    end-of-season rule says so, else to gold. -/
def checkGroup (rules : List RuleVersion) (spans : List (Nat × Nat × Nat))
    (ms : List Move)
    (st : SeasonState) (rk : Ranking) : Bool :=
  let group := movesOf ms st.season st.player
  let idxOk := nonDecreasing (group.map (·.roundIdx))
  let (ok, hpFinal, goldFinal) := chainFold rules spans st.hpStart st.goldStart group
  match endRule rules ms st.season st.player with
  | none =>
    -- No moves in this (season, player) group (monthly structure,
    -- 2026-11-24: S6 has 3 moves for 24 active players, so most S6
    -- groups are empty, as are MANUS/ZHIPU/MINIMAX in S5; the old
    -- structure had no empty group). The end must equal the start,
    -- with no penalty (borrowed is 0), and the ranking must match.
    -- `ok`, `hpFinal`, `goldFinal` are the chainFold results on the
    -- empty group (true, hpStart, goldStart).
    idxOk && ok &&
    hpFinal == st.hpEnd && goldFinal == st.goldEnd &&
    st.penalty == 0 &&
    hpFinal == rk.hpEnd && goldFinal == rk.goldEnd &&
    st.season == rk.season && st.player == rk.player
  | some er =>
    let pen := st.borrowed * (er.penaltyNumer : Int) / (er.penaltyDenom : Int)
    let hpEnd := if er.penaltyAppliesToHp then capHp er (hpFinal - pen)
                 else hpFinal
    let goldEnd := if er.penaltyAppliesToHp then goldFinal
                   else goldFinal - pen
    idxOk && ok &&
    0 ≤ st.borrowed && st.penalty == pen &&
    hpEnd == st.hpEnd && goldEnd == st.goldEnd &&
    hpEnd == rk.hpEnd && goldEnd == rk.goldEnd &&
    st.season == rk.season && st.player == rk.player

/-- C1: counts. Seasons carry their own round counts, move totals
    and active rosters; nothing about the number of seasons or
    players is hard-coded. Monthly structure (2026-11-24): a round
    holds a variable number of moves, so the move total and the
    per-season move totals are checked against the recorded season
    move counts, and the distinct round indices per season against
    the round counts. The old per-(season, player) == rounds
    equality assumed one move per player per round and does not
    apply. -/
def checkCounts (ms : List Move) (seasons : List SeasonInfo) : Bool :=
  ms.length ==
    (seasons.foldl (fun acc s => acc + s.moves) 0)
  &&
  seasons.all fun s =>
    (ms.filter fun m => m.season == s.season).length == s.moves
  &&
  seasons.all fun s =>
    (distinct ((ms.filter fun m => m.season == s.season)
      |>.map (·.roundIdx))).length == s.rounds

/-- C2/C3/C9: ledger over all (season, player) groups. -/
def checkLedger (rules : List RuleVersion) (spans : List (Nat × Nat × Nat))
    (ms : List Move)
    (states : List SeasonState) (rankings : List Ranking) : Bool :=
  states.all fun st =>
    match rankings.find? fun r =>
      r.season == st.season && r.player == st.player with
    | none => false
    | some rk => checkGroup rules spans ms st rk

/-- C4: a player at 0 HP at a season end must not act afterwards. -/
def checkElimination (ms : List Move) (rankings : List Ranking) : Bool :=
  rankings.all fun r =>
    if r.hpEnd == 0 then
      (ms.filter fun m => m.season > r.season && m.player == r.player).isEmpty
    else true

/-- C5: no move or card may predate its true date; no key card may
    first appear while a rule version in effect makes it unavailable. -/
def checkTime (rules : List RuleVersion) (ms : List Move)
    (minDates : List (Nat × Nat))
    (cardFirstDates : List (String × Nat))
    (cardMinDates : List (String × Nat)) : Bool :=
  ms.all fun m =>
    match minDates.find? fun kv => kv.1 == m.actionKind with
    | none => true
    | some (_, d) => decide (d ≤ m.date)
  &&
  cardFirstDates.all fun (card, first) =>
    match cardMinDates.find? fun kv => kv.1 == card with
    | none => true
    | some (_, d) => decide (d ≤ first)
  &&
  cardFirstDates.all fun (card, first) =>
    !(rules.any fun r =>
      ruleInEffect r first && r.unavailableCards.contains card)

/-- Is this holding of a shared key card (same cost and card name as
    a `KeyCard` with `shared = true`)? Mirrors `check.py` C6:
    `shared_keys` is keyed by `(cost, card)`. -/
def isSharedHolding (cards : List KeyCard) (h : Holding) : Bool :=
  cards.any fun kc => kc.shared && kc.cost == h.cost && kc.card == h.card

/-- Per-cost pool count under distinct-card counting (decision
    2026-11-21, Gu approved): a shared card counts once per
    `(cost, card)`, however many players hold it; a non-shared card
    counts once per holding row, as before. -/
def poolCount (holdings : List Holding) (cards : List KeyCard)
    (cost : Nat) : Nat :=
  let sharedDistinct := distinct
    ((holdings.filter fun h => h.cost == cost && isSharedHolding cards h)
      |>.map (·.card))
  let nonShared :=
    (holdings.filter fun h => h.cost == cost && !isSharedHolding cards h)
      |>.length
  sharedDistinct.length + nonShared

/-- C6: card pool. Per-cost distinct cards held <= pool total; key
    cards have at most one holder unless shared; star-weighted copies
    per card fit the pool. The weighted synthesis check is unchanged:
    it does not fail on the real trace, and changing it is out of
    scope. -/
def checkPool (holdings : List Holding) (pool : List (Nat × Nat))
    (cards : List KeyCard) : Bool :=
  pool.all fun (cost, total) =>
    decide (poolCount holdings cards cost ≤ total)
  &&
  cards.all fun kc =>
    (kc.shared || kc.holders.length ≤ 1) &&
    let weighted := (holdings.filter fun h => h.card == kc.card).foldl
      (fun acc h => acc + 3 ^ (h.stars - 1)) 0
    match pool.find? fun kv => kv.1 == kc.cost with
    | none => true
    | some (_, total) => decide (weighted ≤ total)

/-- C7: facts arithmetic. -/
def checkFacts (ipo : IpoFacts) (nv : NvdaFacts) : Bool :=
  ipo.basePlusPrivateUsdM == ipo.baseUsdM + ipo.privateUsdM &&
  ipo.combinedUsdM == ipo.greenshoeTotalUsdM + ipo.privateUsdM &&
  (nv.closeHighCents - nv.lowCents) * 1000 / nv.closeHighCents
    == nv.closeDropTenthsPct &&
  (nv.intradayHighCents - nv.lowCents) * 1000 / nv.intradayHighCents
    == nv.intradayDropTenthsPct

/-- C8: roster. Every round holds a subset of the season's active
    players (monthly structure, 2026-11-24: a round holds a variable
    number of moves; the old equality -- every round holds exactly
    the active set -- assumed one move per player per round);
    rankings complete; no legacy id among player names. -/
def checkRoster (ms : List Move) (rankings : List Ranking)
    (seasons : List SeasonInfo) (playerNames : List String)
    (legacyIds : List String) : Bool :=
  seasons.all fun s =>
    let rounds := (ms.filter fun m => m.season == s.season)
      |>.map (·.roundIdx) |> distinct
    rounds.all fun ridx =>
      ((ms.filter fun m => m.season == s.season &&
        m.roundIdx == ridx) |>.map (·.player) |> distinct).all
        fun p => s.activePlayers.contains p
  &&
  rankings.length ==
    (seasons.foldl (fun acc s => acc + s.activePlayers.length) 0)
  &&
  playerNames.all fun name => !legacyIds.contains name

/-- C9: chart lines equal the rankings' HP ends. A player's point
    position is its index among the seasons in which it is active. -/
def checkChart (hpSeries : List (List Int)) (rankings : List Ranking)
    (seasons : List SeasonInfo) : Bool :=
  rankings.all fun r =>
    match hpSeries[r.player]? with
    | none => false
    | some line =>
      let activeSeasons := seasons.filter fun s =>
        s.activePlayers.contains r.player
      let pos := (activeSeasons.map (·.season)).idxOf r.season
      match line[pos]? with
      | none => false
      | some v => v == r.hpEnd

/-- C10: every rule action matches the political record (doc number,
    issuing body, effective date) and the mechanics table (same rule
    id + version, same effective window); stated goal is present and
    in the enum. -/
def checkMetaC10 (rules : List RuleVersion) (actions : List RuleAction)
    (records : List PoliticalRecord) : Bool :=
  actions.all fun ra =>
    ra.statedGoal ≤ 4 && ra.docNumber != "" && ra.issuedBy != "" &&
    (records.any fun rec =>
      rec.docNumber == ra.docNumber && rec.issuingBody == ra.issuedBy &&
      rec.effectiveDate == ra.effectiveFrom) &&
    (rules.any fun r =>
      r.id == ra.ruleId && r.version == ra.version &&
      r.effectiveFrom == ra.effectiveFrom &&
      r.effectiveTo == ra.effectiveTo)

/-- Date of a trigger reference: a move's date, or the event's date. -/
def refDate (ms : List Move) (ref : TriggerRef) : Option Nat :=
  if ref.isMove then
    (ms.find? fun m => m.season == ref.season && m.player == ref.player &&
      m.roundIdx == ref.roundIdx).map (·.date)
  else some ref.date

/-- Does a trigger reference point at something that exists? -/
def refExists (ms : List Move) (ref : TriggerRef) : Bool :=
  if ref.isMove then
    ms.any fun m => m.season == ref.season && m.player == ref.player &&
      m.roundIdx == ref.roundIdx
  else ref.eventId != ""

/-- C11: the reflexive loop. Every link's references exist; dates are
    ordered observe < rule effective <= react < observe again; a
    rule action whose trigger event is an event id must name the
    observed event; every rule action is linked or carries a trigger. -/
def checkMetaC11 (ms : List Move) (actions : List RuleAction)
    (links : List TriggerLink) : Bool :=
  links.all fun lk =>
    match actions.find? fun ra => ra.ruleId == lk.ruleAction with
    | none => false
    | some ra =>
      refExists ms lk.observe && refExists ms lk.react &&
      (if lk.hasAgain then refExists ms lk.observeAgain else true) &&
      match refDate ms lk.observe, refDate ms lk.react with
      | some dObs, some dReact =>
        decide (dObs < ra.effectiveFrom) &&
        decide (ra.effectiveFrom ≤ dReact) &&
        (if lk.hasAgain then
          match refDate ms lk.observeAgain with
          | some dAgain => decide (dReact < dAgain)
          | none => false
        else true) &&
        (if lk.observe.isMove then true
         else if ra.triggerEvent.startsWith "evt-" then
           ra.triggerEvent == lk.observe.eventId
         else true)
      | _, _ => false
  &&
  actions.all fun ra =>
    (links.any fun lk => lk.ruleAction == ra.ruleId) ||
      ra.triggerEvent != ""

/-- Two rule versions have identical mechanics parameters. -/
def ruleParamsEq (a b : RuleVersion) : Bool :=
  a.hpCap == b.hpCap && a.hpFloor == b.hpFloor &&
  a.penaltyNumer == b.penaltyNumer && a.penaltyDenom == b.penaltyDenom &&
  a.penaltyAppliesToHp == b.penaltyAppliesToHp &&
  a.bannedKinds == b.bannedKinds &&
  a.unavailableCards == b.unavailableCards

/-- The previous global rule version before `r`, if any. -/
def prevGlobalRule (rules : List RuleVersion) (r : RuleVersion)
    : Option RuleVersion :=
  (rules.filter fun x =>
    x.targets.isEmpty && x.effectiveFrom < r.effectiveFrom).foldl
    (fun acc x => match acc with
      | none => some x
      | some y => if x.effectiveFrom > y.effectiveFrom then some x
                  else some y)
    none

/-- C12: dual roles and stated-goal consistency.
    `goalChecks` is a list of (goal, requirement): 0 restrictive (the
    rule must ban an action kind or make a card unavailable), 1 public
    (the action must carry a public doc number), 2 param_change (the
    version must change at least one mechanic parameter vs the
    previous global version). -/
def checkMetaC12 (rules : List RuleVersion) (mps : List MetaPlayer)
    (actions : List RuleAction) (lobbies : List LobbyAction)
    (goalChecks : List (Nat × Nat)) (nPlayers : Nat) : Bool :=
  actions.all fun ra =>
    match mps.find? fun mp => mp.id == ra.actor with
    | none => false
    | some mp => mp.layer2Role == 0
  &&
  mps.all fun mp =>
    if mp.kind ≤ 3 then mp.layer1Role == 0 else true
  &&
  lobbies.all fun lb =>
    lb.actor < nPlayers &&
    (actions.any fun ra => ra.ruleId == lb.targetRule) &&
    lb.position ≤ 2
  &&
  actions.all fun ra =>
    goalChecks.all fun (goal, req) =>
      if goal != ra.statedGoal then true
      else if req == 0 then
        match rules.find? fun r =>
          r.id == ra.ruleId && r.version == ra.version with
        | none => false
        | some r => !r.bannedKinds.isEmpty || !r.unavailableCards.isEmpty
      else if req == 1 then
        ra.docNumber != ""
      else if req == 2 then
        match rules.find? fun r =>
          r.id == ra.ruleId && r.version == ra.version with
        | none => false
        | some r =>
          match prevGlobalRule rules r with
          | none => true
          | some prev => !ruleParamsEq prev r
      else true

end Jjc
