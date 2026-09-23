// Frame contract prahari.frame/1 (SPEC §4.6). The dashboard knows only this contract.

export interface NodeInfo { id: number; x: number; y: number; type: string }
export interface Gateway { id: string; x: number; y: number }
export interface ModelCardRow {
  model: string; kind: string; equation: string; tag: string;
  description: string; version: string; source: string;
}
export interface Header {
  schema: string; label: string; scenario: string; description: string;
  seed: number; start: string; days: number; tick_minutes: number; n_ticks: number;
  record_every: number;
  map: { width_m: number; height_m: number; interfaces: { kind: string; points: [number, number][] }[] };
  spacing_m: number; radius_m: number;
  nodes: NodeInfo[]; gateways: Gateway[];
  modules: Record<string, string>;
  model_card: ModelCardRow[];
}
export interface FrameEvent { type: string; node?: number; fire?: number; module?: string; error?: string; trace_id?: string; x?: number; y?: number }
export interface Alert { level: string; cluster: number[]; trace_id: string }
export interface FireState { id: number; x: number; y: number; area_m2: number; age_min: number; q: number }
export interface Frame {
  t: number;
  weather: { T: number; RH: number; wind_ms: number; wind_dir_deg: number; rain_mm: number; ffmc: number };
  prior: { odds: number; quorum: number; day_type: string };
  nodes: { state: number[]; reading: number[]; residual: number[]; p: number[]; cusum: number[]; health: number[]; soc: number[] };
  cusum_h: number;
  fires: FireState[];
  packets: { from: number; to: string | null; ok: boolean; sf: number | null }[];
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
