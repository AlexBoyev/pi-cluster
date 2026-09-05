export type ChannelType = "webhook" | "email";
export type MinSeverity = "warning" | "critical";

export interface NotificationChannel {
  id: number;
  name: string;
  channel_type: ChannelType;
  url: string | null;
  email_address: string | null;
  min_severity: MinSeverity;
  enabled: boolean;
  created_at: string;
}
