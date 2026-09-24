import { goTo, usePresenter } from "../components/PresenterOverlay";
import { FIRENET_WORDS, TEAM, TEAM_LOGO } from "./brand";
import { orderedSteps } from "./PresenterTouch";
import "./site.css";
import "./mobile.css";

/** Thin bar above the header strip: what FIRENET stands for, and the team behind it (public site only). */
export function SiteBar() {
  return (
    <div className="site-bar" data-testid="site-bar">
      <p className="site-bar-name">
        <b className="site-bar-firenet">FIRENET</b>
        <span className="site-bar-expansion">
          {FIRENET_WORDS.map(({ word, key }, i) => (
            <span key={i}>
              {i ? " " : ""}
              {key ? <><b>{key}</b>{word.slice(key.length)}</> : word}
            </span>
          ))}
        </span>
      </p>
      <TourButton />
      <p className="site-bar-team">
        <span className="muted">a project by</span>
        <img src={TEAM_LOGO} alt="" width={22} height={22} />
        <b>{TEAM.name}</b>
      </p>
    </div>
  );
}

/** Starts the storyboard (presenter mode) at step 1, so visitors without keys 1–9 can follow it; hidden during it. */
function TourButton() {
  const board = usePresenter((s) => s.board);
  const step = usePresenter((s) => s.step);
  if (!board || step) return null;
  return (
    <button className="site-tour" data-testid="site-tour" onClick={() => void goTo(orderedSteps(board)[0])}>
      ▶ Guided tour <span className="muted">· {board.steps.length} steps</span>
    </button>
  );
}

/** The header's product name on the public site: FIRENET, with the simulator's name beneath it. */
export function SiteBrand() {
  return (
    <span className="brand-name site-brand" data-testid="site-brand">
      FIRENET
      <span className="site-brand-sub">PRAHARI-SIM</span>
    </span>
  );
}
