-- State transition system for the Jin Chan Chan replay page (schema v4).
-- The finite checks in `Model.lean` verify one trace (558 moves).
-- This module proves the universal statement: ANY trajectory generated
-- by the transition relation preserves the invariants. The 558-move
-- trace is one instance of that theorem, checked by `native_decide`.
--
-- State: per-player HP, gold, elimination, liability, population,
-- holdings, current rule version, date, season; plus meta-game state
-- (payoffs per rule-maker) and knowledge (what each party knows, and
-- what each party knows that all know -- common knowledge, depth 2).
--
-- Transitions: round actions (lobby play under the rules), rule
-- changes (the meta-game acts first and sets the rules), lobbying
-- (companies act in layer 2), season settlement (leverage penalty).
-- Lobby results feed back into meta-game payoffs; payoffs stay in
-- [-10, 10] or the step is illegal.
--
-- Scope conditions, carried explicitly as hypotheses (checked by
-- `native_decide` for the real trace, via `rulesWellFormed`):
-- (a) every rule has hpFloor <= hpCap;
-- (b) rule ids are unique in the table;
-- (c) all rules share the same HP cap and floor (true of every
-- version so far; a future rule that changes the cap needs a
-- clamp-on-change step, which is a small, explicit extension).
-- No `sorry`, no axioms beyond Lean's own.
import Verification.Model

namespace Jjc

/-- Point update of a list (core Lean has no `List.set` in 4.36). -/
def listUpd {α} [Inhabited α] : List α → Nat → α → List α
  | [], _, _ => []
  | _ :: xs, 0, v => v :: xs
  | x :: xs, n + 1, v => x :: listUpd xs n v

theorem listUpd_length {α} [Inhabited α] (xs : List α) (i : Nat) (v : α) :
    (listUpd xs i v).length = xs.length := by
  induction xs generalizing i with
  | nil => simp [listUpd]
  | cons x xs ih =>
    cases i with
    | zero => simp [listUpd]
    | succ i => simp [listUpd, ih]

theorem listUpd_get_same {α} [Inhabited α] (xs : List α) (i : Nat) (v : α)
    (h : i < xs.length) : (listUpd xs i v).getD i default = v := by
  induction xs generalizing i with
  | nil => simp at h
  | cons x xs ih =>
    cases i with
    | zero => simp [listUpd]
    | succ i =>
      simp only [listUpd, List.getD_cons_succ]
      exact ih (by simp at h ⊢; exact h)

theorem listUpd_get_other {α} [Inhabited α] (xs : List α) (i j : Nat)
    (v : α) (hi : i < xs.length) (hj : j < xs.length) (hne : i ≠ j) :
    (listUpd xs i v).getD j default = xs.getD j default := by
  induction xs generalizing i j with
  | nil => simp at hi
  | cons x xs ih =>
    cases i with
    | zero =>
      cases j with
      | zero => exact absurd rfl hne
      | succ j => simp [listUpd]
    | succ j =>
      cases j with
      | zero => simp [listUpd]
      | succ j =>
        simp only [listUpd, List.getD_cons_succ]
        exact ih (by simp at hi ⊢; exact hi) (by simp at hj ⊢; exact hj)
          (by intro h; exact hne (by simp [h]))

theorem listUpd_get_self {α} [Inhabited α] (xs : List α) (i : Nat)
    (h : i < xs.length) : listUpd xs i (xs.getD i default) = xs := by
  induction xs generalizing i with
  | nil => simp at h
  | cons x xs ih =>
    cases i with
    | zero => simp [listUpd]
    | succ i =>
      simp only [listUpd, List.getD_cons_succ]
      rw [ih (by simp at h ⊢; exact h)]

theorem getD_map_of_lt {α β} [Inhabited α] [Inhabited β] (f : α → β)
    (xs : List α) {i : Nat} (hi : i < xs.length) (d : β) :
    (xs.map f).getD i d = f (xs.getD i default) := by
  induction xs generalizing i with
  | nil => simp at hi
  | cons x xs ih =>
    cases i with
    | zero => simp
    | succ i => simp [ih (by simp at hi ⊢; exact hi)]

theorem getD_eq_default {α} [Inhabited α] (xs : List α) {i : Nat}
    (h : xs.length ≤ i) (d : α) : xs.getD i d = d := by
  induction xs generalizing i with
  | nil => rfl
  | cons x xs ih =>
    cases i with
    | zero => simp at h
    | succ i => simp [ih (by simp at h ⊢; exact h)]

/-- From `(List.range n).all P = true`, read off `P i` for `i < n`. -/
theorem all_range_get {n : Nat} {P : Nat → Bool}
    (h : (List.range n).all P = true) {i : Nat} (hi : i < n) :
    P i = true :=
  List.all_eq_true.mp h i (List.mem_range.mpr hi)

/-- From `(l.all P) = true`, read off `P x` for `x ∈ l`. -/
theorem all_mem_get {α} {l : List α} {P : α → Bool}
    (h : l.all P = true) {x : α} (hx : x ∈ l) : P x = true :=
  List.all_eq_true.mp h x hx

/-- `(a == b) = true` means `a = b`. -/
theorem beq_eq {α} [BEq α] [LawfulBEq α] {a b : α} (h : (a == b) = true) :
    a = b :=
  beq_iff_eq.mp h

/-- HP clamp under one rule version. -/
theorem capHp_bounds {r : RuleVersion} {x : Int} (h : r.hpFloor ≤ r.hpCap) :
    r.hpFloor ≤ capHp r x ∧ capHp r x ≤ r.hpCap := by
  constructor <;> simp only [capHp] <;> omega

/-- Season settlement: apply one leverage penalty per player, then
    clamp. Eliminated players stay at 0. -/
def settleAll : List Int → List Bool → List Int → RuleVersion →
    List Int × List Bool
  | [], [], [], _ => ([], [])
  | h :: hs, e :: es, p :: ps, r =>
    let h' := if e then 0 else capHp r (h - p)
    let (hs', es') := settleAll hs es ps r
    (h' :: hs', (e || h' == 0) :: es')
  | _, _, _, _ => ([], [])

theorem settleAll_fst_length {hs : List Int} {es : List Bool}
    {ps : List Int} {r : RuleVersion}
    (h1 : hs.length = es.length) (h2 : hs.length = ps.length) :
    (settleAll hs es ps r).1.length = hs.length := by
  induction hs generalizing es ps with
  | nil =>
    cases es with
    | nil => cases ps with | nil => rfl | cons _ _ => simp at h2
    | cons _ _ => simp at h1
  | cons h hs ih =>
    cases es with
    | nil => simp at h1
    | cons e es =>
      cases ps with
      | nil => simp at h2
      | cons p ps =>
        simp only [settleAll]
        have := ih (by simp at h1 ⊢; exact h1)
          (by simp at h2 ⊢; exact h2)
        simp [this]

theorem settleAll_snd_length {hs : List Int} {es : List Bool}
    {ps : List Int} {r : RuleVersion}
    (h1 : hs.length = es.length) (h2 : hs.length = ps.length) :
    (settleAll hs es ps r).2.length = es.length := by
  induction hs generalizing es ps with
  | nil =>
    cases es with
    | nil => cases ps with | nil => rfl | cons _ _ => simp at h2
    | cons _ _ => simp at h1
  | cons h hs ih =>
    cases es with
    | nil => simp at h1
    | cons e es =>
      cases ps with
      | nil => simp at h2
      | cons p ps =>
        simp only [settleAll]
        have := ih (by simp at h1 ⊢; exact h1)
          (by simp at h2 ⊢; exact h2)
        simp [this]

theorem settleAll_fst_get {hs : List Int} {es : List Bool}
    {ps : List Int} {r : RuleVersion}
    (h1 : hs.length = es.length) (h2 : hs.length = ps.length) {i : Nat}
    (hi : i < hs.length) :
    (settleAll hs es ps r).1.getD i 0 =
      if es.getD i false then 0
      else capHp r (hs.getD i 0 - ps.getD i 0) := by
  induction hs generalizing es ps i with
  | nil => simp at hi
  | cons h hs ih =>
    cases es with
    | nil => simp at h1
    | cons e es =>
      cases ps with
      | nil => simp at h2
      | cons p ps =>
        cases i with
        | zero => simp [settleAll]
        | succ i =>
          simp only [settleAll, List.getD_cons_succ]
          rw [ih (by simp at h1 ⊢; exact h1)
            (by simp at h2 ⊢; exact h2) (by simp at hi ⊢; exact hi)]
          simp

theorem settleAll_snd_get {hs : List Int} {es : List Bool}
    {ps : List Int} {r : RuleVersion}
    (h1 : hs.length = es.length) (h2 : hs.length = ps.length) {i : Nat}
    (hi : i < hs.length) :
    (settleAll hs es ps r).2.getD i false =
      (es.getD i false ||
        (settleAll hs es ps r).1.getD i 0 == 0) := by
  induction hs generalizing es ps i with
  | nil => simp at hi
  | cons h hs ih =>
    cases es with
    | nil => simp at h1
    | cons e es =>
      cases ps with
      | nil => simp at h2
      | cons p ps =>
        cases i with
        | zero => simp [settleAll]
        | succ i =>
          simp only [settleAll, List.getD_cons_succ]
          rw [ih (by simp at h1 ⊢; exact h1)
            (by simp at h2 ⊢; exact h2) (by simp at hi ⊢; exact hi)]

/-- How many copies of card `c` are held across all players. -/
def cardCount (css : List (List String)) (c : String) : Nat :=
  (css.flatten.filter (· == c)).length

theorem cardCount_upd_append {css : List (List String)} {i : Nat}
    {d c : String} (hi : i < css.length) :
    cardCount (listUpd css i (css.getD i [] ++ [d])) c =
      cardCount css c + (if c == d then 1 else 0) := by
  induction css generalizing i with
  | nil => simp at hi
  | cons x xs ih =>
    cases i with
    | zero =>
      simp only [listUpd, List.getD_cons_zero, cardCount, List.flatten_cons,
        List.filter_append, List.length_append]
      by_cases hcd : c == d <;> simp [hcd, List.filter_append,
        List.length_append]
    | succ i =>
      have hi' : i < xs.length := by simp at hi ⊢; exact hi
      simp only [listUpd, List.getD_cons_succ, cardCount,
        List.flatten_cons, List.filter_append, List.length_append]
      rw [ih hi']
      simp [List.filter_append, List.length_append]
      by_cases hcd : c == d <;> simp [hcd] <;> omega

theorem flatten_length_upd_append {css : List (List String)} {i : Nat}
    {d : String} (hi : i < css.length) :
    (listUpd css i (css.getD i [] ++ [d])).flatten.length =
      css.flatten.length + 1 := by
  induction css generalizing i with
  | nil => simp at hi
  | cons x xs ih =>
    cases i with
    | zero =>
      simp [listUpd, List.flatten_cons, List.length_append]
    | succ i =>
      have hi' : i < xs.length := by simp at hi ⊢; exact hi
      simp only [listUpd, List.getD_cons_succ, List.flatten_cons,
        List.length_append]
      rw [ih hi']
      omega

theorem cardCount_le_flatten (css : List (List String)) (c : String) :
    cardCount css c ≤ css.flatten.length := by
  simp only [cardCount]
  exact List.length_filter_le _ _

/-- The full game state: lobby state + meta-game state + knowledge. -/
structure GState where
  hp : List Int
  gold : List Int
  elim : List Bool
  liab : List Bool
  pop : List Nat
  cards : List (List String)
  rule : Nat
  date : Nat
  season : Nat
  payoffs : List Int
  known : List (List Nat)
  known2 : List (List Nat)
  deriving DecidableEq, Repr, Inhabited

/-- Static context: the rule table, the card pool, the parties. -/
structure Ctx where
  rules : List RuleVersion
  keyCards : List String
  sharedCards : List String
  publicRules : List Nat
  nPlayers : Nat
  nMeta : Nat
  nParties : Nat
  deriving DecidableEq, Repr, Inhabited

/-- One transition. `round` is lobby play; `ruleChange` is the
    meta-game acting; `lobby` is a company acting in layer 2;
    `settle` is season-end leverage settlement. -/
inductive GAction where
  | round (player season : Nat) (hpD goldD : Int) (kind date pop : Nat)
      (card : String) (liab : Bool) (rv : Nat)
  | ruleChange (ruleId version date actor : Nat) (public : Bool)
      (payoffDelta : List Int) (action : Nat)
  | lobby (actor targetRule position date : Nat) (payoffDelta : List Int)
  | settle (season date : Nat) (penalties : List Int)
  deriving DecidableEq, Repr, Inhabited

/-- Payoffs stay in [-10, 10]. -/
def payoffInRange (ps : List Int) : Bool :=
  ps.all fun p => -10 ≤ p && p ≤ 10

/-- One player's safety properties under one explicit rule version. -/
def playerInvRule (rv : RuleVersion) (hp gold : Int) (elim liab : Bool) :
    Bool :=
  decide (rv.hpFloor ≤ hp) &&
  decide (hp ≤ rv.hpCap) &&
  (decide (0 ≤ gold) || liab) &&
  (if elim then hp == 0 else true) &&
  (if hp == 0 then elim else true)

/-- Same HP bounds give the same verdict (used when the rule version
    changes but the bounds do not). -/
theorem playerInvRule_congr {r1 r2 : RuleVersion} {hp gold : Int}
    {elim liab : Bool}
    (h : r1.hpCap = r2.hpCap ∧ r1.hpFloor = r2.hpFloor) :
    playerInvRule r1 hp gold elim liab =
      playerInvRule r2 hp gold elim liab := by
  simp [playerInvRule, h.1, h.2]

/-- A player satisfies the safety properties in this state. -/
def playerInv (ctx : Ctx) (s : GState) (i : Nat) : Bool :=
  match ctx.rules.find? fun x => x.id == s.rule with
  | none => false
  | some rv => playerInvRule rv (s.hp.getD i 0) (s.gold.getD i 0)
      (s.elim.getD i false) (s.liab.getD i false)

/-- Invariants other than common knowledge. -/
def invCore (ctx : Ctx) (s : GState) : Bool :=
  s.hp.length == ctx.nPlayers && s.gold.length == ctx.nPlayers &&
  s.elim.length == ctx.nPlayers && s.liab.length == ctx.nPlayers &&
  s.pop.length == ctx.nPlayers && s.cards.length == ctx.nPlayers &&
  s.payoffs.length == ctx.nMeta &&
  s.known.length == ctx.nParties && s.known2.length == ctx.nParties &&
  payoffInRange s.payoffs &&
  (List.range ctx.nPlayers).all (playerInv ctx s) &&
  (match ctx.rules.find? fun x => x.id == s.rule with
   | none => false
   | some rv => decide (rv.effectiveFrom ≤ s.date)) &&
  (ctx.keyCards.all fun c =>
    cardCount s.cards c ≤
      (if ctx.sharedCards.contains c then ctx.keyCards.length else 1)) &&
  decide (s.cards.flatten.length ≤ ctx.keyCards.length)

/-- Common knowledge: every public rule version effective by now is
    known by every party, and known by every party to be known by all. -/
def invKnow (ctx : Ctx) (s : GState) : Bool :=
  ctx.publicRules.all fun rid =>
    match ctx.rules.find? fun x => x.id == rid with
    | none => true
    | some rv =>
      if rv.effectiveFrom ≤ s.date then
        (List.range ctx.nParties).all fun p =>
          (s.known.getD p []).contains rid &&
          (s.known2.getD p []).contains rid
      else true

/-- All invariants: safety properties + temporal properties
    (HP never negative, eliminated never returns, a rule version
    applies only on/after its effective date) + common knowledge. -/
def inv (ctx : Ctx) (s : GState) : Bool := invCore ctx s && invKnow ctx s

/-- Add facts to a knowledge set (no duplicates). -/
def addFact (fs : List Nat) (ks : List Nat) : List Nat :=
  fs.foldl (fun acc f => if acc.contains f then acc else acc ++ [f]) ks

theorem mem_foldl_addFact {fs : List Nat} {f : Nat} {ks : List Nat}
    (h : f ∈ ks) : f ∈ addFact fs ks := by
  induction fs generalizing ks with
  | nil => exact h
  | cons g gs ih =>
    simp only [addFact, List.foldl_cons]
    apply ih
    by_cases hc : ks.contains g
    · simp [hc]; exact h
    · simp [hc]
      exact List.mem_append_of_mem_left h _

theorem mem_addFact {fs : List Nat} {f : Nat} {ks : List Nat}
    (h : f ∈ fs) : f ∈ addFact fs ks := by
  induction fs generalizing ks with
  | nil => simp at h
  | cons g gs ih =>
    simp only [addFact, List.foldl_cons]
    cases h with
    | head =>
      apply mem_foldl_addFact
      by_cases hc : ks.contains g
      · simp [hc]
      · simp [hc]
    | tail _ htail => exact ih htail

/-- Public rule versions effective by `date`, as fact ids. -/
def newFacts (ctx : Ctx) (d : Nat) : List Nat :=
  ctx.publicRules.filter fun rid =>
    match ctx.rules.find? fun x => x.id == rid with
    | some rv => decide (rv.effectiveFrom ≤ d)
    | none => false

/-- A public rule is common knowledge once it takes effect: add every
    public fact effective by `date` to every party's knowledge
    (level 1 and level 2). -/
def learnPublic (ctx : Ctx) (s : GState) (date : Nat) : GState :=
  { s with
    known := s.known.map (addFact (newFacts ctx date)),
    known2 := s.known2.map (addFact (newFacts ctx date)) }

theorem mem_newFacts {ctx : Ctx} {rid : Nat} {rv : RuleVersion}
    {d : Nat} (hpub : rid ∈ ctx.publicRules)
    (hfind : ctx.rules.find? fun x => x.id == rid = some rv)
    (heff : rv.effectiveFrom ≤ d) : rid ∈ newFacts ctx d := by
  apply List.mem_filter.mpr
  constructor
  · exact hpub
  · simp [hfind, heff]

/-- After `learnPublic`, every public fact effective by `d` is common
    knowledge (given the state date is no later than `d` and the
    knowledge lists have one entry per party). -/
theorem learnPublic_know (ctx : Ctx) (s : GState) (d : Nat)
    (hle : s.date ≤ d)
    (hlen : s.known.length = ctx.nParties ∧
            s.known2.length = ctx.nParties) :
    invKnow ctx (learnPublic ctx s d) = true := by
  apply List.all_eq_true.mpr
  intro rid hrid
  cases hfind : ctx.rules.find? fun x => x.id == rid with
  | none =>
    simp only [invKnow, learnPublic]
    simp [hfind]
  | some rv =>
    by_cases heff : rv.effectiveFrom ≤ s.date
    · have heff' : rv.effectiveFrom ≤ d := le_trans heff hle
      have hmem : rid ∈ newFacts ctx d :=
        mem_newFacts hrid hfind heff'
      simp only [invKnow, learnPublic]
      simp only [hfind, heff, ↓reduceIte]
      apply List.all_eq_true.mpr
      intro p hp
      have hp_lt : p < ctx.nParties := List.mem_range.mp hp
      have h1 : rid ∈ addFact (newFacts ctx d) (s.known.getD p []) :=
        mem_addFact hmem
      have h2 : rid ∈ addFact (newFacts ctx d) (s.known2.getD p []) :=
        mem_addFact hmem
      have e1 : ((s.known.map (addFact (newFacts ctx d))).getD p []) =
          addFact (newFacts ctx d) (s.known.getD p []) :=
        getD_map_of_lt _ _ (by rw [hlen.1]; exact hp_lt) _
      have e2 : ((s.known2.map (addFact (newFacts ctx d))).getD p []) =
          addFact (newFacts ctx d) (s.known2.getD p []) :=
        getD_map_of_lt _ _ (by rw [hlen.2]; exact hp_lt) _
      rw [e1, e2]
      simp [List.contains_eq_mem.mpr h1, List.contains_eq_mem.mpr h2]
    · simp only [invKnow, learnPublic]
      simp [hfind, heff]

/-- `learnPublic` preserves the core invariants (it only touches
    knowledge) and establishes common knowledge. -/
theorem learnPublic_inv (ctx : Ctx) (s : GState) (date : Nat) :
    invCore ctx s = true → s.date = date →
    inv ctx (learnPublic ctx s date) = true := by
  intro hcore hdate
  have hlen : s.known.length = ctx.nParties ∧
      s.known2.length = ctx.nParties := by
    simp only [invCore, Bool.and_eq_true] at hcore
    exact ⟨hcore.2.2.2.2.2.2.2.1, hcore.2.2.2.2.2.2.2.2.1⟩
  have hcore' : invCore ctx (learnPublic ctx s date) = true := by
    simpa [learnPublic, List.length_map] using hcore
  have hknow : invKnow ctx (learnPublic ctx s date) = true :=
    learnPublic_know ctx s date (by rw [hdate]) hlen
  simp only [inv, Bool.and_eq_true]
  exact ⟨hcore', hknow⟩

/-- `baseRuleAt` returns a rule from the table, in effect at the date. -/
theorem baseRuleAt_some {rules : List RuleVersion} {d : Nat}
    {r : RuleVersion} (h : baseRuleAt rules d = some r) :
    r ∈ rules ∧ r.targets = [] ∧ ruleInEffect r d = true := by
  have key : ∀ (l : List RuleVersion) (acc : Option RuleVersion),
      (l.foldl (fun a x => match a with
        | none => some x
        | some y => if x.effectiveFrom > y.effectiveFrom then some x
                    else some y) acc = some r) →
      (r ∈ l ∨ acc = some r) := by
    intro l acc
    induction l generalizing acc with
    | nil => simp
    | cons x xs ih =>
      intro hf
      simp only [List.foldl_cons] at hf
      cases acc with
      | none =>
        have := ih (some x) hf
        cases this with
        | inl hm => exact Or.inl (List.mem_cons_of_mem x hm)
        | inr hm => exact Or.inl (by simp [Option.some.inj hm])
      | some y =>
        by_cases hcmp : x.effectiveFrom > y.effectiveFrom
        · have := ih (some x) (by simp [hcmp] at hf; exact hf)
          cases this with
          | inl hm => exact Or.inl (List.mem_cons_of_mem x hm)
          | inr hm => exact Or.inl (by simp [Option.some.inj hm])
        · have := ih (some y) (by simp [hcmp] at hf; exact hf)
          cases this with
          | inl hm => exact Or.inl (List.mem_cons_of_mem x hm)
          | inr hm => exact Or.inr hm
  unfold baseRuleAt at h
  have hmem := key (rules.filter fun r =>
    r.targets.isEmpty && ruleInEffect r date) none h
  cases hmem with
  | inl hm =>
    have hm2 := List.mem_filter.mp hm
    refine ⟨List.mem_of_mem_filter hm, ?_, ?_⟩
    · have := hm2.2
      simp [Bool.and_eq_true] at this
      exact this.1
    · have := hm2.2
      simp [Bool.and_eq_true] at this
      exact this.2
  | inr hm => simp at hm

/-- A rule found by id in a table with unique ids is the rule itself. -/
theorem find?_id_eq {rules : List RuleVersion} {r : RuleVersion}
    (huniq : ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.id = r2.id → r1 = r2)
    (hmem : r ∈ rules) :
    rules.find? fun x => x.id == r.id = some r := by
  rw [List.find?_eq_some_iff]
  constructor
  · exact hmem
  · simp

/-- Well-formedness of a rule table, as one Bool: uniform HP bounds,
    floor <= cap, unique ids. -/
def rulesWellFormed (rules : List RuleVersion) : Bool :=
  rules.all (fun r => decide (r.hpFloor ≤ r.hpCap)) &&
  rules.all (fun r1 => rules.all (fun r2 =>
    if r1.id == r2.id then r1 == r2 else true)) &&
  rules.all (fun r1 => rules.all (fun r2 =>
    decide (r1.hpCap = r2.hpCap) && decide (r1.hpFloor = r2.hpFloor)))

theorem rulesWellFormed_floor {rules : List RuleVersion}
    (h : rulesWellFormed rules = true) :
    ∀ r ∈ rules, r.hpFloor ≤ r.hpCap := by
  intro r hr
  simp only [rulesWellFormed, Bool.and_eq_true] at h
  have := all_mem_get h.1 hr
  exact decide_eq_true_eq.mp this

theorem rulesWellFormed_uniq {rules : List RuleVersion}
    (h : rulesWellFormed rules = true) :
    ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.id = r2.id → r1 = r2 := by
  intro r1 r2 hr1 hr2 hid
  simp only [rulesWellFormed, Bool.and_eq_true] at h
  have h1 := all_mem_get h.2.1 hr1
  have h2 := all_mem_get h1 hr2
  simp [hid] at h2
  exact beq_eq h2

theorem rulesWellFormed_uniform {rules : List RuleVersion}
    (h : rulesWellFormed rules = true) :
    ∀ r1 r2 : RuleVersion, r1 ∈ rules → r2 ∈ rules →
      r1.hpCap = r2.hpCap ∧ r1.hpFloor = r2.hpFloor := by
  intro r1 r2 hr1 hr2
  simp only [rulesWellFormed, Bool.and_eq_true] at h
  have h1 := all_mem_get h.2.2 hr1
  have h2 := all_mem_get h1 hr2
  simp only [Bool.and_eq_true, decide_eq_true_eq] at h2
  exact h2

end Jjc

namespace Jjc

/-- One round step. The acting player must be alive, the date and
    season must not go backwards, the recorded rule version must be
    the version in effect at the date, no banned action kind may be
    used, gold must stay >= 0 unless the move is flagged liability,
    and a gained key card must be new (unless shared) and fit the pool. -/
def stepRound (ctx : Ctx) (s : GState) (player season : Nat)
    (hpD goldD : Int) (kind date pop : Nat) (card : String) (liab : Bool)
    (rv : Nat) : Option GState :=
  match baseRuleAt ctx.rules date with
  | none => none
  | some base =>
    if player < ctx.nPlayers && !s.elim.getD player false &&
       decide (s.date ≤ date) && decide (s.season ≤ season) &&
       rv == base.id &&
       !(base.bannedKinds.contains kind) &&
       !((overlaysAt ctx.rules date player).any fun ov =>
         ov.bannedKinds.contains kind) &&
       (decide (0 ≤ s.gold.getD player 0 + goldD) || liab) &&
       (card == "" || (ctx.keyCards.contains card &&
         (ctx.sharedCards.contains card || cardCount s.cards card == 0) &&
         s.cards.flatten.length < ctx.keyCards.length)) then
      let hp' := capHp base (s.hp.getD player 0 + hpD)
      let s1 := { s with
        hp := listUpd s.hp player hp',
        gold := listUpd s.gold player (s.gold.getD player 0 + goldD),
        elim := listUpd s.elim player
          (s.elim.getD player false || hp' == 0),
        liab := listUpd s.liab player liab,
        pop := listUpd s.pop player pop,
        cards := listUpd s.cards player
          (if card == "" then s.cards.getD player []
           else s.cards.getD player [] ++ [card]),
        rule := base.id,
        date := date,
        season := season }
      some (learnPublic ctx s1 date)
    else none

/-- One rule change at the rule table. A global enact/amend resets
    the lobby's current rule; a rescind or an overlay leaves the
    current rule to the version in effect at the date (or unchanged
    if none is in effect). Payoffs move; a public change is common
    knowledge via `learnPublic`, a private one only reaches its actor. -/
def stepRuleChange (ctx : Ctx) (s : GState) (ruleId version date actor : Nat)
    (public : Bool) (payoffDelta : List Int) (action : Nat) :
    Option GState :=
  match ctx.rules.find? fun x => x.id == ruleId && x.version == version with
  | none => none
  | some rv =>
    let payoffs' := (s.payoffs.zip payoffDelta).map fun (a, b) => a + b
    if decide (rv.effectiveFrom ≤ date) && decide (s.date ≤ date) &&
       actor < ctx.nParties && payoffDelta.length == ctx.nMeta &&
       payoffInRange payoffs' then
      let rule' :=
        if rv.targets.isEmpty && action != 2 then ruleId
        else (match baseRuleAt ctx.rules date with
              | some b => b.id
              | none => s.rule)
      let s1 := { s with
        rule := rule',
        date := date,
        payoffs := payoffs',
        known := if public then s.known else
          listUpd s.known actor
            (let ks := s.known.getD actor []
             if ks.contains ruleId then ks else ks ++ [ruleId]) }
      some (learnPublic ctx s1 date)
    else none

/-- One lobbying action: a company acts in layer 2. Private knowledge
    only; payoffs move. -/
def stepLobby (ctx : Ctx) (s : GState) (actor targetRule position date : Nat)
    (payoffDelta : List Int) : Option GState :=
  let payoffs' := (s.payoffs.zip payoffDelta).map fun (a, b) => a + b
  if actor < ctx.nPlayers && decide (s.date ≤ date) &&
     decide (ctx.nMeta + actor < ctx.nParties) &&
     (ctx.rules.any fun x => x.id == targetRule) &&
     position ≤ 2 && payoffDelta.length == ctx.nMeta &&
     payoffInRange payoffs' then
    let party := ctx.nMeta + actor
    let fact := 10000 + targetRule
    let s1 := { s with
      date := date,
      payoffs := payoffs',
      known := listUpd s.known party
        (let ks := s.known.getD party []
         if ks.contains fact then ks else ks ++ [fact]) }
    some (learnPublic ctx s1 date)
  else none

/-- Season settlement: leverage penalty on HP for every player, under
    the rule version in effect at the settlement date. -/
def stepSettle (ctx : Ctx) (s : GState) (season date : Nat)
    (penalties : List Int) : Option GState :=
  match baseRuleAt ctx.rules date with
  | none => none
  | some base =>
    if decide (s.date ≤ date) && decide (s.season ≤ season) &&
       penalties.length == ctx.nPlayers then
      let (hp', elim') := settleAll s.hp s.elim penalties base
      let s1 := { s with hp := hp', elim := elim', rule := base.id,
                   date := date, season := season }
      some (learnPublic ctx s1 date)
    else none

/-- The transition relation, as a computable function. -/
def step (ctx : Ctx) (s : GState) (a : GAction) : Option GState :=
  match a with
  | .round player season hpD goldD kind date pop card liab rv =>
    stepRound ctx s player season hpD goldD kind date pop card liab rv
  | .ruleChange ruleId version date actor public payoffDelta action =>
    stepRuleChange ctx s ruleId version date actor public payoffDelta action
  | .lobby actor targetRule position date payoffDelta =>
    stepLobby ctx s actor targetRule position date payoffDelta
  | .settle season date penalties => stepSettle ctx s season date penalties

/-- Run a trajectory: the list of states after each action, or `none`
    if any step is illegal. -/
def runStates : Ctx → GState → List GAction → Option (List GState)
  | _, _, [] => some []
  | ctx, s, a :: rest =>
    match step ctx s a with
    | none => none
    | some s' => (s' :: ·) <$> runStates ctx s' rest

/-- The whole trajectory is legal and every visited state satisfies
    the invariants. -/
def trajectoryOk (ctx : Ctx) (s0 : GState) (acts : List GAction) : Bool :=
  match runStates ctx s0 acts with
  | none => false
  | some states => states.all (inv ctx)

/-- The meta-game acts first: every round uses a rule version that was
    enacted by an earlier rule change (or is in the initial set). -/
def metaOrderOk : List GAction → List Nat → Bool
  | [], _ => true
  | a :: rest, enacted =>
    match a with
    | .round _ _ _ _ _ _ _ _ _ rv =>
      enacted.contains rv && metaOrderOk rest enacted
    | .ruleChange ruleId _ _ _ _ _ _ =>
      metaOrderOk rest (enacted ++ [ruleId])
    | _ => metaOrderOk rest enacted

end Jjc
