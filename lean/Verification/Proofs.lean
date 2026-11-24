import Verification.Model
import Verification.Dynamics
import Verification.Trace

-- Theorems: every invariant holds on the whole trace.
-- Each theorem is one invariant class, discharged by `native_decide`
-- over the machine-generated trace data in `Trace.lean`.
-- C1-C9 cover layer 1 (market game); C10-C12 cover layer 2
-- (meta-game / rule table). A successful `lake build` is the proof
-- certificate. Nothing is sampled: every theorem quantifies over
-- the complete trace.

namespace Jjc

/-- C1: counts (moves total, per (season, player), rounds per season).
    Seasons carry their own round counts and rosters. -/
theorem counts_ok :
    checkCounts traceMoves traceSeasons = true := by
  native_decide

/-- C2/C3/C9: HP/gold ledger under the rule version in effect at each
    move's date (per-move chain, season ends, rankings match). -/
theorem ledger_ok :
    checkLedger traceRules traceRoundSpans traceMoves traceStates
      traceRankings = true := by
  native_decide

/-- C4: elimination. -/
theorem elimination_ok :
    checkElimination traceMoves traceRankings = true := by
  native_decide

/-- C5: dates; no card first appears while a rule version in effect
    makes it unavailable. -/
theorem time_ok :
    checkTime traceRules traceMoves traceMinDates traceCardFirstDates
      traceCardMinDates = true := by
  native_decide

/-- C6: card pool. -/
theorem pool_ok :
    checkPool traceHoldings tracePool traceKeyCards = true := by
  native_decide

/-- C7: facts arithmetic (IPO stages, NVDA drops). -/
theorem facts_ok : checkFacts traceIpo traceNvda = true := by
  native_decide

/-- C8: roster completeness (per-season active players), no legacy ids. -/
theorem roster_ok :
    checkRoster traceMoves traceRankings traceSeasons
      tracePlayers traceLegacyIds = true := by
  native_decide

/-- C9: chart lines equal the rankings' HP ends. -/
theorem chart_ok :
    checkChart traceHpSeries traceRankings traceSeasons = true := by
  native_decide

/-- C10: every rule action matches the political record (doc number,
    issuing body, effective date) and the mechanics table. -/
theorem meta_record_ok :
    checkMetaC10 traceRules traceRuleActions
      tracePoliticalRecords = true := by
  native_decide

/-- C11: the reflexive loop observe -> rule -> react -> observe again. -/
theorem meta_triggers_ok :
    checkMetaC11 traceMoves traceRuleActions
      traceTriggerLinks = true := by
  native_decide

/-- C12: dual roles (government is referee in layer 1, player in
    layer 2; companies are players in layer 1, lobbyists in layer 2)
    and stated-goal consistency. -/
theorem meta_roles_ok :
    checkMetaC12 traceRules traceMetaPlayers traceRuleActions
      traceLobbyActions traceGoalChecks traceNPlayers = true := by
  native_decide

/-- D-layer: the rule table itself is well formed (HP floor <= cap
    per version, version ids unique). Instance check. -/
theorem trace_rules_wellformed :
    dynRulesOk traceRules = true := by
  native_decide

/-- D-layer: every recorded initial state (one per (player, season)
    segment) satisfies the dynamic invariant under the rule table.
    Instance check, written in the `all_range_get` form so the
    universal link below can read it off. -/
theorem trace_initial_ok :
    (List.range traceDynInit.length).all
      (fun i => dynInvariant traceRules (traceDynInit.getD i default))
      = true := by
  native_decide

/-- D-layer: every recorded season segment's move list runs legally
    from its initial state (the season opening), and every visited
    state satisfies the dynamic invariant. Instance check. -/
theorem trace_trajectory_ok :
    checkDynamics traceRules traceRoundSpans traceDynInit traceMoves
      = true := by
  native_decide

/-- D-layer link: the 751 recorded moves are ONE instance of the
    unbounded theorem. For any recorded initial state, any move list
    of any length (past rounds and future rounds to 2030 alike), a
    legal run from that initial state ends in a state satisfying the
    invariant. Proved from `invariant_run` by induction, not by
    deciding the recorded trace. -/
theorem dynamics_trace_via_universal :
    ∀ (i : Nat) (_hi : i < traceDynInit.length) (ms : List Move)
      (s' : DState),
      run traceRules traceRoundSpans (traceDynInit.getD i default) ms
        = some s' →
      dynInvariant traceRules s' = true := by
  intro i hi ms s' hrun
  have hinit : dynInvariant traceRules (traceDynInit.getD i default)
      = true :=
    all_range_get trace_initial_ok hi
  exact invariant_run traceRules traceRoundSpans
    (dynRulesOk_floor trace_rules_wellformed)
    (dynRulesOk_uniq trace_rules_wellformed) ms _ s' hinit hrun

/-- D-layer link: every intermediate state of any run from a
    recorded initial state, over that initial state's own segment
    moves, satisfies the invariant. -/
theorem trace_states_satisfy_invariants :
    ∀ (i : Nat) (_hi : i < traceDynInit.length) (states : List DState),
      runStates traceRules traceRoundSpans (traceDynInit.getD i default)
        (traceMoves.filter fun m => m.player ==
          (traceDynInit.getD i default).player &&
          m.season == (traceDynInit.getD i default).season)
        = some states →
      states.all (dynInvariant traceRules) = true := by
  intro i hi states hrun
  have hinit : dynInvariant traceRules (traceDynInit.getD i default)
      = true :=
    all_range_get trace_initial_ok hi
  exact invariant_runStates traceRules traceRoundSpans
    (dynRulesOk_floor trace_rules_wellformed)
    (dynRulesOk_uniq trace_rules_wellformed) _ _ _ hinit hrun

/-- Headline: all 12 invariant classes hold on the whole trace. -/
theorem all_invariants_hold :
    checkCounts traceMoves traceSeasons &&
    checkLedger traceRules traceRoundSpans traceMoves traceStates
      traceRankings &&
    checkElimination traceMoves traceRankings &&
    checkTime traceRules traceMoves traceMinDates traceCardFirstDates
      traceCardMinDates &&
    checkPool traceHoldings tracePool traceKeyCards &&
    checkFacts traceIpo traceNvda &&
    checkRoster traceMoves traceRankings traceSeasons
      tracePlayers traceLegacyIds &&
    checkChart traceHpSeries traceRankings traceSeasons &&
    checkMetaC10 traceRules traceRuleActions tracePoliticalRecords &&
    checkMetaC11 traceMoves traceRuleActions traceTriggerLinks &&
    checkMetaC12 traceRules traceMetaPlayers traceRuleActions
      traceLobbyActions traceGoalChecks traceNPlayers &&
    dynRulesOk traceRules &&
    (List.range traceDynInit.length).all
      (fun i => dynInvariant traceRules (traceDynInit.getD i default)) &&
    checkDynamics traceRules traceRoundSpans traceDynInit traceMoves
      = true := by
  native_decide

end Jjc
