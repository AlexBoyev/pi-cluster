export interface ThrottleReading {
  elapsed_seconds: number;
  throttled_hex: string;
  undervoltage_now: boolean;
  freq_capped_now: boolean;
  throttled_now: boolean;
  undervoltage_occurred: boolean;
  throttled_occurred: boolean;
  temp_celsius: number | null;
  volts: number | null;
}

export type StressVerdict =
  | "clean"
  | "undervoltage_under_load"
  | "throttled_under_load"
  | "crashed_or_unreachable"
  | "unknown";

export interface NodeStressResult {
  node_name: string;
  ip_address: string;
  reachable: boolean;
  error: string | null;
  ncores: number | null;
  baseline: ThrottleReading | null;
  samples: ThrottleReading[];
  final: ThrottleReading | null;
  max_temp_celsius: number | null;
  min_volts: number | null;
  undervoltage_detected: boolean;
  throttled_detected: boolean;
  verdict: StressVerdict;
}

export interface StressTestReport {
  started_at: string;
  duration_seconds: number;
  nodes: NodeStressResult[];
  any_undervoltage: boolean;
  any_node_unreachable: boolean;
  summary: string;
}
