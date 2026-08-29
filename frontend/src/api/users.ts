import type { UserProfile } from "../types/user";
import { apiFetch } from "./client";

export const listUsers = () => apiFetch<UserProfile[]>("/users/");

export const createUser = (username: string, password: string, role: string) =>
  apiFetch<UserProfile>("/users/", {
    method: "POST",
    body: JSON.stringify({ username, password, role }),
  });

export const updateUserRole = (userId: number, role: string) =>
  apiFetch<UserProfile>(`/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });

export const changeUserPassword = (userId: number, newPassword: string) =>
  apiFetch<UserProfile>(`/users/${userId}/password`, {
    method: "PATCH",
    body: JSON.stringify({ new_password: newPassword }),
  });

export const deleteUser = (userId: number) =>
  apiFetch<void>(`/users/${userId}`, { method: "DELETE" });
