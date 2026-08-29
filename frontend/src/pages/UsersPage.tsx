import { FormEvent, useEffect, useState } from "react";
import { changeUserPassword, createUser, deleteUser, listUsers, updateUserRole } from "../api/users";
import { useAuth } from "../context/AuthContext";
import type { UserProfile } from "../types/user";
import "./UsersPage.css";

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function UsersPage() {
  const { username: currentUsername } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingPw, setEditingPw] = useState<number | null>(null);
  const [pwValue, setPwValue] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const [form, setForm] = useState({ username: "", password: "", role: "viewer" });

  const refresh = () =>
    listUsers()
      .then((u) => { setUsers(u); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { refresh(); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createUser(form.username, form.password, form.role);
      setForm({ username: "", password: "", role: "viewer" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  async function handleRoleChange(user: UserProfile, role: string) {
    try {
      await updateUserRole(user.id, role);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update role");
    }
  }

  async function handlePasswordSave(userId: number) {
    if (!pwValue.trim()) return;
    setPwSaving(true);
    setError(null);
    try {
      await changeUserPassword(userId, pwValue.trim());
      setEditingPw(null);
      setPwValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to change password");
    } finally {
      setPwSaving(false);
    }
  }

  async function handleDelete(userId: number) {
    setDeletingId(userId);
    setError(null);
    try {
      await deleteUser(userId);
      setConfirmDelete(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete user");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="usr-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total users</div>
          <div className="summ-value sv-blue">{users.length}</div>
          <div className="summ-sub">registered accounts</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Admins</div>
          <div className="summ-value sv-green">{users.filter(u => u.role === "admin").length}</div>
          <div className="summ-sub">full access</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Viewers</div>
          <div className="summ-value sv-amber">{users.filter(u => u.role === "viewer").length}</div>
          <div className="summ-sub">read-only access</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Create user</span>
      </div>
      <div className="usr-form-card">
        <form className="usr-form" onSubmit={handleCreate}>
          <div className="usr-field">
            <label className="usr-label">Username</label>
            <input
              className="usr-input"
              placeholder="johndoe"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              pattern="^[a-zA-Z0-9_-]{3,64}$"
              required
              disabled={creating}
            />
          </div>
          <div className="usr-field">
            <label className="usr-label">Password</label>
            <input
              className="usr-input"
              type="password"
              placeholder="min 8 chars"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              minLength={8}
              required
              disabled={creating}
            />
          </div>
          <div className="usr-field">
            <label className="usr-label">Role</label>
            <select
              className="usr-input"
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              disabled={creating}
            >
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="usr-field usr-field-submit">
            <button className="usr-btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create user"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Users</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading users…</span></div>
      ) : (
        <div className="usr-table-wrap">
          <table className="usr-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = u.username === currentUsername;
                return (
                  <tr key={u.id} className={isSelf ? "usr-row-self" : ""}>
                    <td>
                      <span className="usr-name">{u.username}</span>
                      {isSelf && <span className="usr-self-tag">you</span>}
                    </td>
                    <td>
                      {isSelf ? (
                        <span className={`usr-role-badge urb-${u.role}`}>{u.role}</span>
                      ) : (
                        <select
                          className={`usr-role-select urs-${u.role}`}
                          value={u.role}
                          onChange={(e) => handleRoleChange(u, e.target.value)}
                        >
                          <option value="viewer">viewer</option>
                          <option value="admin">admin</option>
                        </select>
                      )}
                    </td>
                    <td>
                      <span className={`usr-status-badge${u.is_active ? " usb-active" : " usb-inactive"}`}>
                        {u.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td className="usr-date">{fmtDate(u.created_at)}</td>
                    <td>
                      <div className="usr-actions">
                        {editingPw === u.id ? (
                          <div className="usr-pw-edit">
                            <input
                              className="usr-pw-input"
                              type="password"
                              placeholder="new password"
                              value={pwValue}
                              onChange={(e) => setPwValue(e.target.value)}
                              minLength={8}
                              autoFocus
                            />
                            <button
                              className="usr-btn-save"
                              onClick={() => handlePasswordSave(u.id)}
                              disabled={pwSaving || pwValue.length < 8}
                            >
                              {pwSaving ? "…" : "Save"}
                            </button>
                            <button
                              className="usr-btn-cancel"
                              onClick={() => { setEditingPw(null); setPwValue(""); }}
                              disabled={pwSaving}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            className="usr-btn-pw"
                            onClick={() => { setEditingPw(u.id); setPwValue(""); }}
                          >
                            Change password
                          </button>
                        )}
                        {!isSelf && (
                          confirmDelete === u.id ? (
                            <div className="usr-confirm">
                              <span className="usr-confirm-txt">Delete {u.username}?</span>
                              <button
                                className="usr-btn-del-confirm"
                                onClick={() => handleDelete(u.id)}
                                disabled={deletingId === u.id}
                              >
                                {deletingId === u.id ? "…" : "Yes, delete"}
                              </button>
                              <button
                                className="usr-btn-cancel"
                                onClick={() => setConfirmDelete(null)}
                              >
                                No
                              </button>
                            </div>
                          ) : (
                            <button
                              className="usr-btn-del"
                              onClick={() => setConfirmDelete(u.id)}
                            >
                              Delete
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
