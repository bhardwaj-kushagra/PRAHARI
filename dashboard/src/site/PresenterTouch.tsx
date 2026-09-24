import type { Step, Storyboard } from "../presenter";

/** The storyboard steps in the order keys 1–9 play them. */
export function orderedSteps(board: Storyboard): Step[] {
  return board.steps.slice().sort((a, b) => a.key - b.key);
}

/** The step before (-1) or after (+1) the current one, or null at either end. */
export function neighbourStep(board: Storyboard, current: Step, dir: -1 | 1): Step | null {
  const steps = orderedSteps(board);
  const i = steps.findIndex((s) => s.key === current.key);
  return i < 0 ? null : steps[i + dir] ?? null;
}

interface Props { board: Storyboard | null; step: Step; go: (s: Step) => void; hide: () => void }

/** Buttons for the presenter caption strip (public site): previous, next and close, for visitors on a phone or tablet
 *  who have no keys 1–9. Rendered by PresenterOverlay; the steps themselves are unchanged. */
export function PresenterTouch({ board, step, go, hide }: Props) {
  if (!board) return null;
  const prev = neighbourStep(board, step, -1);
  const next = neighbourStep(board, step, 1);
  return (
    <nav className="presenter-touch" aria-label="Guided tour steps" data-testid="presenter-touch">
      <button onClick={() => prev && go(prev)} disabled={!prev}>◀ Previous</button>
      <button onClick={() => next && go(next)} disabled={!next} className="presenter-next">Next ▶</button>
      <button onClick={hide} aria-label="End the guided tour">✕</button>
    </nav>
  );
}
