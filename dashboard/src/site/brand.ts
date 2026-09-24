// Names shown by the public site (site branches only; see docs/site/README.md). Kept in one place so the
// page, the tests and the link-preview tags in index.html say the same thing.

/** The system's name and what it stands for: FI-RE-N-E-T. `key` marks the letters that make up the acronym. */
export const FIRENET_WORDS: { word: string; key: string }[] = [
  { word: "Fire", key: "F" },
  { word: "Identification", key: "I" },
  { word: "and", key: "" },
  { word: "Response", key: "Re" },
  { word: "Network", key: "N" },
  { word: "for", key: "" },
  { word: "Early", key: "E" },
  { word: "Tracking", key: "T" },
];

export const FIRENET_EXPANSION = FIRENET_WORDS.map((w) => w.word).join(" ");

/** The team's name only. Its website is left out until the developer adds it back (docs/site/LOG.md, S4). */
export const TEAM = { name: "AgniWare" };

/** The team logo, bundled with the site (no request to another host). */
export const TEAM_LOGO = `${import.meta.env.BASE_URL}brand/agniware-96.png`;
