import type { ClusterCapacity } from "../types/cluster";
import { apiFetch } from "./client";

export const getClusterCapacity = () => apiFetch<ClusterCapacity>("/cluster/capacity");
