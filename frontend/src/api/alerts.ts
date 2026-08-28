import type { Alert } from "../types/alert";
import { apiFetch } from "./client";

export const listAlerts = () => apiFetch<Alert[]>("/alerts/");
