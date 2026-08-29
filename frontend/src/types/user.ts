export interface UserProfile {
  id: number;
  username: string;
  role: "admin" | "viewer";
  is_active: boolean;
  created_at: string;
}
