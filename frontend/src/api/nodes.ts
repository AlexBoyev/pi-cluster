import type { Node } from "../types/node";
import { apiFetch } from "./client";

export const getNodes = () => apiFetch<Node[]>("/nodes/");
export const getNode = (id: number) => apiFetch<Node>(`/nodes/${id}`);
