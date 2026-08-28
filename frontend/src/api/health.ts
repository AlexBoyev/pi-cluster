import type { NodeHealth } from "../types/node";
import { apiFetch } from "./client";

export const getAllHealth = () => apiFetch<NodeHealth[]>("/health/");
export const getNodeHealth = (id: number) => apiFetch<NodeHealth>(`/health/${id}`);
