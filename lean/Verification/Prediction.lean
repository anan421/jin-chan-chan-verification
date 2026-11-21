-- Prediction layer for the Jin Chan Chan replay page.
-- Design: `design/prediction-layer.md`, section 6.
-- This file proves conditional facts about a given strategy.
-- It does not prove that any player follows that strategy.
-- The strategy itself comes from the game model plus backtest.
-- That claim is a model claim, not a Lean theorem.
--
-- Scope:
-- - A strategy depends only on the current state (MPE form).
-- - A payoff is abstract: `DState -> Move -> Int`.
-- - Concrete payoff parameters live in `rules/payoff-model.json`.
-- - Lean uses only the quantified form of the payoff.
-- - `Move` gains no payoff or population field (design section 8,
--   item 9). Population and card holdings stay in the finite layer.
-- - Gold is never clamped. A negative gold result needs a
--   liability flag. This comes from `Dynamics.lean`, unchanged.
-- - Proofs use induction, in the shape of `invariant_run`.
-- - No proof enumerates the future with `decide`.
import Verification.Dynamics

namespace Jjc

/-- A single-step strategy (design section 2, MPE form).
    A multi-step game folds this function with `runStrategy`. -/
abbrev Strategy := DState → Move

/-- An abstract payoff function (design section 2).
    The concrete parameters live outside Lean, in the payoff model
    file. Lean uses only this quantified form. -/
abbrev Payoff := DState → Move → Int

/-- Best response to the predicted moves of the other players.
    `u` is the payoff with the predicted others already folded in:
    the caller builds `u` from the full payoff `U s a others`.
    The list `others` is carried in the signature so the call site
    shows which prediction the response answers. The argmax itself
    reads only the current state `s`, never the history. That is
    the MPE strategy form. The empty candidate list gives `none`. -/
def bestResponse (u : Payoff) (s : DState) (_others : List Move) :
    List Move → Option Move
  | [] => none
  | m :: rest =>
    match bestResponse u s _others rest with
    | none => some m
    | some b => if u s m > u s b then some m else some b

/-- The best response to an empty candidate list is `none`. -/
theorem bestResponse_nil (u : Payoff) (s : DState) (others : List Move) :
    bestResponse u s others [] = none := rfl

/-- The best response is `none` exactly when the candidate list
    is empty. -/
theorem bestResponse_eq_none_iff (u : Payoff) (s : DState)
    (others : List Move) (cands : List Move) :
    bestResponse u s others cands = none ↔ cands = [] := by
  induction cands with
  | nil => simp [bestResponse]
  | cons m rest ih =>
    constructor
    · intro h
      simp only [bestResponse] at h
      cases hrest : bestResponse u s others rest with
      | none => simp [hrest] at h
      | some b =>
        by_cases hcmp : u s m > u s b <;> simp [hrest, hcmp] at h
    · intro h
      simp at h

/-- The best response, when it exists, is one of the candidates. -/
theorem bestResponse_mem (u : Payoff) (s : DState) (others : List Move)
    (cands : List Move) :
    ∀ {m : Move}, bestResponse u s others cands = some m → m ∈ cands := by
  induction cands with
  | nil =>
    intro m h
    simp [bestResponse] at h
  | cons a rest ih =>
    intro m h
    simp only [bestResponse] at h
    cases hrest : bestResponse u s others rest with
    | none =>
      simp [hrest] at h
      subst h
      exact List.mem_cons_self
    | some b =>
      by_cases hcmp : u s a > u s b
      · simp [hrest, hcmp] at h
        subst h
        exact List.mem_cons_self
      · simp [hrest, hcmp] at h
        subst h
        exact List.mem_cons_of_mem a (ih hrest)

/-- The best response maximises the payoff over the candidates. -/
theorem bestResponse_max (u : Payoff) (s : DState) (others : List Move)
    (cands : List Move) :
    ∀ {m : Move}, bestResponse u s others cands = some m →
    ∀ a ∈ cands, u s a ≤ u s m := by
  induction cands with
  | nil =>
    intro m h
    simp [bestResponse] at h
  | cons a rest ih =>
    intro m h
    simp only [bestResponse] at h
    cases hrest : bestResponse u s others rest with
    | none =>
      simp [hrest] at h
      subst h
      intro x hx
      simp only [List.mem_cons] at hx
      cases hx with
      | inl heq => subst heq; exact Int.le_refl _
      | inr hmem =>
        have hnil : rest = [] :=
          (bestResponse_eq_none_iff u s others rest).mp hrest
        subst hnil
        simp at hmem
    | some b =>
      by_cases hcmp : u s a > u s b
      · simp [hrest, hcmp] at h
        subst h
        intro x hx
        simp only [List.mem_cons] at hx
        cases hx with
        | inl heq => subst heq; exact Int.le_refl _
        | inr hmem =>
          exact Int.le_trans (ih hrest x hmem) (Int.le_of_lt hcmp)
      · simp [hrest, hcmp] at h
        subst h
        intro x hx
        simp only [List.mem_cons] at hx
        cases hx with
        | inl heq => subst heq; exact Int.le_of_not_gt hcmp
        | inr hmem => exact ih hrest x hmem

/-- Run a strategy for `n` steps from a state.
    Each step applies `σ` to the current state, then `applyMove`.
    A failed step gives `none`. The step-first form makes the
    induction below peel one step at a time. -/
def runStrategy : List RuleVersion → Strategy → DState → Nat →
    Option DState
  | _, _, s, 0 => some s
  | rules, σ, s, n + 1 =>
    match applyMove rules s (σ s) with
    | none => none
    | some s' => runStrategy rules σ s' n

/-- (a) A strategy run preserves the invariant.
    The start state satisfies `dynInvariant`. Every step succeeds.
    Then the end state satisfies `dynInvariant`. The proof is
    induction on `n`, with `invariant_apply` at each step. -/
theorem runStrategy_invariant (rules : List RuleVersion)
    (hfloor : ∀ r ∈ rules, r.hpFloor ≤ r.hpCap)
    (huniq : ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.id = r2.id → r1 = r2) :
    ∀ (σ : Strategy) (n : Nat) (s s' : DState),
    dynInvariant rules s = true → runStrategy rules σ s n = some s' →
    dynInvariant rules s' = true := by
  intro σ n
  induction n with
  | zero =>
    intro s s' hinv hrun
    simp only [runStrategy, Option.some.injEq] at hrun
    subst hrun
    exact hinv
  | succ n ih =>
    intro s s' hinv hrun
    simp only [runStrategy] at hrun
    cases hstep : applyMove rules s (σ s) with
    | none => simp [hstep] at hrun
    | some s1 =>
      simp only [hstep] at hrun
      exact ih s1 s'
        (invariant_apply rules hfloor huniq s (σ s) s1 hinv hstep) hrun

/-- A set `S` of states is closed under a strategy `σ`: one step
    from a state in `S` stays in `S`. This is the invariant-set
    notion of design section 3. -/
def strategyClosed (rules : List RuleVersion) (σ : Strategy)
    (S : DState → Prop) : Prop :=
  ∀ s, S s → ∀ s', applyMove rules s (σ s) = some s' → S s'

/-- (b) A run that starts inside a closed set stays inside it.
    Any step count `n` gives an end state in `S`. The proof is
    induction on `n`. Every prefix length is covered, so the whole
    trajectory stays in `S`. -/
theorem runStrategy_mem_closed (rules : List RuleVersion) (σ : Strategy)
    (S : DState → Prop) (hclosed : strategyClosed rules σ S) :
    ∀ (n : Nat) (s s' : DState), S s → runStrategy rules σ s n = some s' →
    S s' := by
  intro n
  induction n with
  | zero =>
    intro s s' hs hrun
    simp only [runStrategy, Option.some.injEq] at hrun
    subst hrun
    exact hs
  | succ n ih =>
    intro s s' hs hrun
    simp only [runStrategy] at hrun
    cases hstep : applyMove rules s (σ s) with
    | none => simp [hstep] at hrun
    | some s1 =>
      simp only [hstep] at hrun
      exact ih s1 s' (hclosed s hs s1 hstep) hrun

/-- The target HP band: the king tier, HP ≥ 90 (design section 3).
    The band uses the page tier map. No new band is invented. -/
def targetBand (s : DState) : Prop := 90 ≤ s.hp

/-- Distance from a state to the target band: the HP points below
    90, else 0. A state above 90 has distance 0. -/
def hpDist (s : DState) : Nat := (90 - s.hp).toNat

/-- The distance is 0 exactly when the state is in the target band. -/
theorem hpDist_eq_zero_iff (s : DState) :
    hpDist s = 0 ↔ targetBand s := by
  simp only [hpDist, targetBand, Int.toNat_eq_zero]
  constructor <;> intro h <;> omega

/-- (c) Entry within a bound: if the distance is at most `k`, the
    strategy enters the target band within `k` steps. The proof is
    induction on the bound `k`. Each step outside the band strictly
    lowers the distance, so the remaining bound shrinks. -/
theorem enter_targetBand_aux (rules : List RuleVersion) (σ : Strategy)
    (hstep : ∀ s, ¬ targetBand s →
      ∃ s', applyMove rules s (σ s) = some s')
    (hdec : ∀ s, ¬ targetBand s → ∀ s',
      applyMove rules s (σ s) = some s' → hpDist s' < hpDist s) :
    ∀ (k : Nat) (s : DState), hpDist s ≤ k →
    ∃ j, j ≤ k ∧ ∃ s', runStrategy rules σ s j = some s' ∧
      targetBand s' := by
  intro k
  induction k with
  | zero =>
    intro s hk
    have h0 : hpDist s = 0 := Nat.le_zero.mp hk
    exact ⟨0, Nat.le_refl 0, s, rfl, (hpDist_eq_zero_iff s).mp h0⟩
  | succ k ih =>
    intro s hk
    by_cases hs : targetBand s
    · exact ⟨0, Nat.zero_le _, s, rfl, hs⟩
    · obtain ⟨s1, h1⟩ := hstep s hs
      have hlt : hpDist s1 < hpDist s := hdec s hs s1 h1
      have hle : hpDist s1 ≤ k := by omega
      obtain ⟨j, hjk, s', hrun, hS⟩ := ih s1 hle
      refine ⟨j + 1, Nat.succ_le_succ hjk, s', ?_, hS⟩
      simp only [runStrategy, h1]
      exact hrun

/-- (c) Entry within the distance: from any state, the strategy
    enters the target band within `hpDist s` steps, when each step
    outside the band succeeds and strictly lowers the distance. -/
theorem enter_targetBand_within (rules : List RuleVersion) (σ : Strategy)
    (hstep : ∀ s, ¬ targetBand s →
      ∃ s', applyMove rules s (σ s) = some s')
    (hdec : ∀ s, ¬ targetBand s → ∀ s',
      applyMove rules s (σ s) = some s' → hpDist s' < hpDist s) :
    ∀ (s : DState),
    ∃ k, k ≤ hpDist s ∧ ∃ s', runStrategy rules σ s k = some s' ∧
      targetBand s' :=
  fun s => enter_targetBand_aux rules σ hstep hdec (hpDist s) s (Nat.le_refl _)

/-- A mixed-strategy distribution is well formed when its weights
    sum to a positive number. The weights are `Nat`; the sum is
    the plain list sum. -/
def validDist (dist : List (Move × Nat)) : Prop :=
  0 < (dist.map Prod.snd).sum

/-- The support of a distribution: the moves that carry a weight,
    in distribution order. -/
def mixSupport (dist : List (Move × Nat)) : List Move :=
  dist.map Prod.fst

/-- (d) Every move in a distribution, from an invariant state, is
    either illegal (`applyMove` gives `none`) or lands in an
    invariant state. The proof is one step of `invariant_apply`.
    The weight sum plays no role in this step: legality of the
    support does not depend on the total weight. The `validDist`
    hypothesis records that the distribution is well formed. -/
theorem mixed_support_invariant (rules : List RuleVersion)
    (hfloor : ∀ r ∈ rules, r.hpFloor ≤ r.hpCap)
    (huniq : ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.id = r2.id → r1 = r2) :
    ∀ (s : DState) (dist : List (Move × Nat)),
    validDist dist → dynInvariant rules s = true →
    ∀ (m : Move) (w : Nat), (m, w) ∈ dist →
    applyMove rules s m = none ∨
      ∃ s', applyMove rules s m = some s' ∧
        dynInvariant rules s' = true := by
  intro s dist _hvalid hinv m w _hmem
  by_cases hnone : applyMove rules s m = none
  · exact Or.inl hnone
  · right
    cases hsome : applyMove rules s m with
    | none => exact absurd hsome hnone
    | some s' =>
      exact ⟨s', rfl,
        invariant_apply rules hfloor huniq s m s' hinv hsome⟩

/-- (d) The same fact, stated for the support list `mixSupport`. -/
theorem mixed_support_invariant_support (rules : List RuleVersion)
    (hfloor : ∀ r ∈ rules, r.hpFloor ≤ r.hpCap)
    (huniq : ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.id = r2.id → r1 = r2) :
    ∀ (s : DState) (dist : List (Move × Nat)),
    validDist dist → dynInvariant rules s = true →
    ∀ m ∈ mixSupport dist,
    applyMove rules s m = none ∨
      ∃ s', applyMove rules s m = some s' ∧
        dynInvariant rules s' = true := by
  intro s dist hvalid hinv m hmem
  rw [mixSupport, List.mem_map] at hmem
  obtain ⟨⟨m', w⟩, hmem', hfst⟩ := hmem
  have hfst' : m' = m := hfst
  rw [← hfst']
  exact mixed_support_invariant rules hfloor huniq s dist hvalid hinv
    m' w hmem'

end Jjc
