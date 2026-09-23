// Frame contract prahari.frame/1 (SPEC §4.6). The dashboard knows only this contract.

export interface NodeInfo { id: number; x: number; y: number; type: string }
export interface Gateway { id: string; x: number; y: number }
export interface ModelCardRow {
  model: string; kind: string; equation: string; tag: string;
  description: string; version: string; source: string;
  notes?: Record<string, unknown>;   // stage snapshot at the start of the run, e.g. calibrated values (DER)
}
// World sections (Phase 1, additive; absent in older recordings)
export interface Interface { kind: "path" | "village" | "road" | "power_line" | string; closed?: boolean; points: [number, number][] }
export interface LambdaGrid { cell_m: number; x0: number; y0: number; nx: number; ny: number; modelled: boolean; values: number[] }
export interface LayoutInfo { covered: number | null; nodes: [number, number][] }
export type LayoutName = "grid" | "corridor" | "greedy";
export type Layouts = { active: LayoutName; corridor_spacing_m: number } & Partial<Record<LayoutName, LayoutInfo>>;
export interface LinkTable {
  modelled: boolean; gateway: (string | null)[]; sf: (number | null)[];
  d_m: number[]; pl_db: number[]; prx_dbm: number[];
  relay?: (number | null)[];   // TS011 relay node for nodes with no direct link (Phase 8)
}

export interface Header {
  schema: string; label: string; scenario: string; description: string;
  seed: number; start: string; days: number; tick_minutes: number; n_ticks: number;
  record_every: number;
  map: { width_m: number; height_m: number; interfaces: Interface[]; lambda_grid?: LambdaGrid };
  spacing_m: number; radius_m: number;
  nodes: NodeInfo[]; gateways: Gateway[];
  modules: Record<string, string>;
  model_card: ModelCardRow[];
  layouts?: Layouts;
  links?: LinkTable;
  detection_radius_m?: number;
  satellite_pixel_m?: number;
  record_from_min?: number;    // warm start: frames begin at this minute (Phase 5 follow-up)
}
export interface FrameEvent { type: string; node?: number; fire?: number; module?: string; error?: string; trace_id?: string; x?: number; y?: number; cause?: string; members?: number[] }
// Plume grid (Phase 3a): float16 little-endian, base64; row 0 is the southern row.
export interface PlumeGrid { x0: number; y0: number; cell_m: number; nx: number; ny: number; max: number; data: string }
export interface Alert { level: string; cluster: number[]; trace_id: string }
/** One uplink attempt (M39–M40). Phase 8 adds kind, retry, time on air, relay, queued and — for packets carried
 *  from ticks between recorded frames — their own minute `t`. `to` is a gateway id or "n<k>" for a relay node. */
export interface Packet {
  from: number; to: string | null; ok: boolean; sf: number | null;
  kind?: "candidate" | "heartbeat"; retry?: number; toa_ms?: number; relay?: number | null; queued?: boolean; t?: number;
}
export interface FireState { id: number; x: number; y: number; area_m2: number; age_min: number; q: number }
export interface Frame {
  t: number;
  weather: { T: number; RH: number; wind_ms: number; wind_dir_deg: number; rain_mm: number; ffmc: number; dew_c?: number };
  prior: { odds: number; quorum: number; day_type: string };
  nodes: { state: number[]; reading: number[]; residual: number[]; p: number[]; cusum: number[]; health: number[]; soc: number[];
           conc?: number[];
           baseline?: number[];      // TTC slow baseline b (M24), Phase 5
           n_cal?: number[];         // QCC calibration-set size n (M26): floor p_min = 1/(n+1), Phase 5
           queue?: number[];         // frames waiting at the node (store-and-forward), Phase 8
           mode?: number[] };        // power mode 0 standard, 1 ULP, 2 off (M43), Phase 8
  plume?: PlumeGrid;
  cusum_h: number;
  haze?: number;               // regional haze level H(t), su (Phase 2)
  fires: FireState[];
  packets: Packet[];
  gateways_down?: string[];    // gateways out of service (Phase 8 outage scenarios)
  events: FrameEvent[];
  alerts: Alert[];
  health: Record<string, string>;
}
export interface ModuleHealthRecord {
  requested: string; state: string; running: string; version: string;
  errors: number; last_error: string; degraded_at: number | null;
}
export interface Footer { frames: number; traces: number; health: Record<string, ModuleHealthRecord> }
export type Trace = Record<string, unknown> & { trace_id: string; t: number; type: string };

export interface Recording { header: Header; frames: Frame[]; traces: Trace[]; footer: Footer | null }

export const SUPPORTED_SCHEMA = "prahari.frame/1";

// Node state codes (SPEC §4.6)
export const NODE_STATE = ["normal", "elevated", "candidate", "confirmed", "fault", "low power"] as const;
