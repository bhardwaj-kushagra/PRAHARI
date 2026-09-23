import { daysLabel } from "../format";
import { useSim } from "../store";

/** Chart/view footer: seeds and simulated days (CLAUDE.md rule 15). */
export function Footer() {
  const source = useSim((s) => s.source);
  if (!source) return <footer className="foot">SIMULATION · no recording loaded</footer>;
  const h = source.header;
  return (
    <footer className="foot" data-testid="footer">
      SIMULATION · seed {h.seed} · {daysLabel(h.days)} · scenario {h.scenario} · {source.frameCount} frames ·
      recording {source.name} · every value shown is simulator output (SIM)
    </footer>
  );
}
