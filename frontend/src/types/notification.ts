export type ChannelType = "webhook" | "email";

export interface NotificationChannel {
  id: number;
  name: string;
  channel_type: ChannelType;
  url: string | null;
  email_address: string | null;
  enabled: boolean;
  created_at: string;
}
