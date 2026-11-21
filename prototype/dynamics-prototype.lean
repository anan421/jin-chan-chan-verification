-- Prototype: unbounded invariant for the TFT replay.
-- Standalone check (not part of the pipeline) that the induction
-- pattern Gu asked about works in Lean 4.36: an invariant proved
-- for ANY move list (any length, any future season), not by
-- deciding one finite 558-move list.
-- Compile: lean prototype-dynamics.lean  (no imports, no Mathlib)

structure State where
  hp : Int
  gold : Int
  deriving DecidableEq, Repr

structure Move where
  dh : Int
  dg : Int

def clampHp (x : Int) : Int := min (max x 0) 100
def clampGold (x : Int) : Int := max x 0

/-- One move applied. HP and gold are clamped, as in Model.lean. -/
def applyMove (s : State) (m : Move) : State :=
  ⟨clampHp (s.hp + m.dh), clampGold (s.gold + m.dg)⟩

/-- Run a whole list of moves (any length) from a state. -/
def run : State → List Move → State
  | s, [] => s
  | s, m :: ms => run (applyMove s m) ms

def Invariant (s : State) : Prop := 0 ≤ s.hp ∧ s.hp ≤ 100 ∧ 0 ≤ s.gold

theorem invariant_apply : ∀ (s : State) (m : Move),
    Invariant s → Invariant (applyMove s m) := by
  intro s m ⟨h0, h100, hg⟩
  refine ⟨?_, ?_, ?_⟩
  · show 0 ≤ min (max (s.hp + m.dh) 0) 100
    omega
  · show min (max (s.hp + m.dh) 0) 100 ≤ 100
    omega
  · show 0 ≤ max (s.gold + m.dg) 0
    omega

/-- The unbounded theorem: the invariant holds after ANY list of
    moves, of any length -- past rounds and future rounds to 2030
    alike. Proved by induction on the list, not by `native_decide`
    over one recorded trace. -/
theorem invariant_run : ∀ (ms : List Move) (s : State),
    Invariant s → Invariant (run s ms) := by
  intro ms s hs
  induction ms generalizing s with
  | nil => exact hs
  | cons m ms ih => exact ih (applyMove s m) (invariant_apply s m hs)
