import { apiFetch } from "./client";
import type { ChannelType, MinSeverity, NotificationChannel } from "../types/notification";

export function listChannels(): Promise<NotificationChannel[]> {
  return apiFetch("/notifications/channels");
}

export function createChannel(data: {
  name: string;
  channel_type: ChannelType;
  url?: string;
  email_address?: string;
  min_severity: MinSeverity;
  enabled: boolean;
}): Promise<NotificationChannel> {
  return apiFetch("/notifications/channels", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateChannel(
  id: number,
  data: Partial<{
    name: string; url: string; email_address: string; min_severity: MinSeverity; enabled: boolean;
  }>
): Promise<NotificationChannel> {
  return apiFetch(`/notifications/channels/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteChannel(id: number): Promise<void> {
  return apiFetch(`/notifications/channels/${id}`, { method: "DELETE" });
}

export function testChannel(id: number): Promise<{ ok: boolean }> {
  return apiFetch(`/notifications/channels/${id}/test`, { method: "POST" });
}
