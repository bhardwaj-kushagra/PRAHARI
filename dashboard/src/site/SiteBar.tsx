import { FIRENET_WORDS, TEAM, TEAM_LOGO } from "./brand";
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
      <a className="site-bar-team" href={TEAM.url} target="_blank" rel="noopener noreferrer"
         title={`${TEAM.name}: ${TEAM.label} (opens in a new tab)`}>
        <span className="muted">a project by</span>
        <img src={TEAM_LOGO} alt="" width={22} height={22} />
        <b>{TEAM.name}</b>
        <span className="site-bar-url">{TEAM.label} ↗</span>
      </a>
    </div>
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
