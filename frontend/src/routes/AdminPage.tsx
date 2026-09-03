import { useEffect, useState } from "react";

import { adminResetPassword, adminRevokeSessions, adminUpdateUser, listUsers } from "../api/client";
import type { AdminUserRecord, AuthUserRecord } from "../api/types";
import { AdminUsersPanel } from "../components/AdminUsersPanel";
import { PersonAvatar } from "../components/PersonAvatar";

type AdminPageProps = {
  currentUser: AuthUserRecord;
};

function formatStorage(storageBytes: number) {
  if (storageBytes >= 1024 ** 3) {
    return `${(storageBytes / 1024 ** 3).toFixed(1)} GB`;
  }
  if (storageBytes >= 1024 ** 2) {
    return `${(storageBytes / 1024 ** 2).toFixed(1)} MB`;
  }
  return `${Math.ceil(storageBytes / 1024)} KB`;
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown" : parsed.toLocaleString();
}

export function AdminPage({ currentUser }: AdminPageProps) {
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState<{ username: string; password: string } | null>(
    null,
  );
  const [busyUserId, setBusyUserId] = useState<number | null>(null);

  const refresh = async () => {
    setIsLoading(true);
    setError(null);
    try {
      setUsers(await listUsers());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load users");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  if (currentUser.role !== "admin") {
    return (
      <section aria-label="Admin page" className="library-page settings-page">
        <div className="library-page__title-block">
          <h2>Admin access required</h2>
          <p>This workspace is only available to administrator accounts.</p>
        </div>
      </section>
    );
  }

  const runUserAction = async (
    userId: number,
    action: () => Promise<unknown>,
    successMessage: string | null = null,
  ) => {
    setActionError(null);
    setStatusMessage(null);
    setBusyUserId(userId);
    try {
      await action();
      if (successMessage) {
        setStatusMessage(successMessage);
      }
      await refresh();
    } catch (responseError) {
      setActionError(responseError instanceof Error ? responseError.message : "Unable to update user");
    } finally {
      setBusyUserId(null);
    }
  };

  return (
    <section aria-label="Admin page" className="library-page settings-page admin-page">
      <div className="library-page__hero settings-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Admin</p>
          <h2>User management</h2>
          <p>
            Invite new readers, manage roles and access, and help people back into their accounts. Admins
            cannot modify their own account from here.
          </p>
        </div>
      </div>

      {isLoading ? <p className="library-page__status-copy">Loading users...</p> : null}
      {error ? (
        <p className="library-page__alert" role="alert">
          {error}
        </p>
      ) : null}
      {actionError ? (
        <p className="library-page__alert" role="alert">
          {actionError}
        </p>
      ) : null}
      {statusMessage ? (
        <p className="library-page__status-copy" role="status">
          {statusMessage}
        </p>
      ) : null}
      {temporaryPassword ? (
        <p className="library-page__status-copy" role="status">
          Temporary password for {temporaryPassword.username}: <code>{temporaryPassword.password}</code> —
          share it privately; it is shown only once and their old sessions are signed out.
        </p>
      ) : null}

      <section className="settings-page__preferences-panel" aria-label="User accounts">
        <div className="settings-page__panel-header">
          <div>
            <p className="library-page__eyebrow">Accounts</p>
            <h3>Everyone on this host</h3>
          </div>
        </div>
        <ul className="library-page__summary admin-page__user-list">
          {users.map((user) => {
            const isSelf = user.id === currentUser.id;
            const isBusy = busyUserId === user.id;
            return (
              <li className="admin-page__user-row" key={user.id}>
                <div className="admin-page__user-identity person-row__identity">
                  <PersonAvatar displayName={user.display_name} />
                  <div>
                  <p className="voices-page__summary-value">
                    {user.display_name} {isSelf ? "(you)" : ""}
                  </p>
                  <p className="voices-page__summary-copy">
                    {user.username} • {user.status} • last sign-in {formatTimestamp(user.last_login_at)}
                  </p>
                  <p className="voices-page__summary-copy">
                    {user.documents_count ?? 0} books • {user.voice_presets_count ?? 0} voice presets •{" "}
                    {user.jobs_count ?? 0} export jobs • {formatStorage(user.storage_bytes ?? 0)} on disk
                  </p>
                  </div>
                </div>
                <div className="admin-page__user-actions">
                  <label className="library-page__field">
                    <span>Role</span>
                    <select
                      aria-label={`Role for ${user.username}`}
                      disabled={isSelf || isBusy}
                      onChange={(event) => {
                        void runUserAction(
                          user.id,
                          () => adminUpdateUser(user.id, { role: event.target.value }),
                          `${user.display_name} is now a ${event.target.value}.`,
                        );
                      }}
                      value={user.role}
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                    </select>
                  </label>
                  <button
                    className="book-card__button book-card__button--ghost"
                    disabled={isSelf || isBusy}
                    onClick={() => {
                      const nextStatus = user.status === "active" ? "disabled" : "active";
                      void runUserAction(
                        user.id,
                        () => adminUpdateUser(user.id, { status: nextStatus }),
                        nextStatus === "disabled"
                          ? `${user.display_name} is disabled and signed out everywhere.`
                          : `${user.display_name} can sign in again.`,
                      );
                    }}
                    type="button"
                  >
                    {user.status === "active" ? "Disable" : "Enable"}
                  </button>
                  <button
                    className="book-card__button book-card__button--ghost"
                    disabled={isSelf || isBusy}
                    onClick={() => {
                      setTemporaryPassword(null);
                      void runUserAction(user.id, async () => {
                        const result = await adminResetPassword(user.id);
                        setTemporaryPassword({
                          username: result.user.username,
                          password: result.temporary_password,
                        });
                      });
                    }}
                    type="button"
                  >
                    Reset password
                  </button>
                  <button
                    className="book-card__button book-card__button--ghost"
                    disabled={isSelf || isBusy}
                    onClick={() => {
                      void runUserAction(
                        user.id,
                        () => adminRevokeSessions(user.id),
                        `${user.display_name} has been signed out everywhere.`,
                      );
                    }}
                    type="button"
                  >
                    Sign out everywhere
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <AdminUsersPanel />
    </section>
  );
}
