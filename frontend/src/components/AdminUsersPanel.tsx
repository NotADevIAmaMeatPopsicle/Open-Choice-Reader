import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import { createInvite, listInvites, revokeInvite } from "../api/client";
import type { UserInviteRecord } from "../api/types";

export function AdminUsersPanel() {
  const [invites, setInvites] = useState<UserInviteRecord[]>([]);
  const [displayNameHint, setDisplayNameHint] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("7");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const refresh = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setInvites(await listInvites());
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Unable to load admin account data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleCreateInvite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setCreatedToken(null);
    setIsSubmitting(true);

    try {
      const createdInvite = await createInvite({
        display_name_hint: displayNameHint.trim() || undefined,
        role_to_grant: "member",
        expires_in_days: expiresInDays.trim() ? Number(expiresInDays) : undefined,
      });
      setCreatedToken(createdInvite.token);
      setDisplayNameHint("");
      await refresh();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Unable to create invite");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeInvite = async (inviteId: number) => {
    setSubmitError(null);
    try {
      await revokeInvite(inviteId);
      await refresh();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Unable to revoke invite");
    }
  };

  return (
    <section className="settings-page__panel" aria-label="Admin invites panel">
      <div className="settings-page__panel-header">
        <div>
          <p className="library-page__eyebrow">Admin</p>
          <h3>Invites</h3>
        </div>
        <p className="settings-page__panel-copy">
          Create invite-only accounts. Share the one-time token privately; the recipient picks their own
          username and password.
        </p>
      </div>

      {loadError ? <p className="library-page__alert" role="alert">{loadError}</p> : null}
      {submitError ? <p className="library-page__alert" role="alert">{submitError}</p> : null}
      {createdToken ? (
        <p className="library-page__status-copy">
          New invite token: <code>{createdToken}</code>
        </p>
      ) : null}

      <form className="voices-page__form" onSubmit={(event) => void handleCreateInvite(event)}>
        <label className="library-page__field">
          <span>Invite display-name hint</span>
          <input onChange={(event) => setDisplayNameHint(event.target.value)} type="text" value={displayNameHint} />
        </label>
        <label className="library-page__field">
          <span>Expires in days</span>
          <input min="1" onChange={(event) => setExpiresInDays(event.target.value)} type="number" value={expiresInDays} />
        </label>
        <button className="book-card__button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Creating invite..." : "Create invite"}
        </button>
      </form>

      <div className="settings-page__defaults-grid">
        <article className="settings-page__summary-card">
          <p className="voices-page__summary-label">Invites</p>
          <p className="voices-page__summary-value">{isLoading ? "Loading..." : invites.length}</p>
          <ul className="library-page__summary">
            {invites.map((invite) => (
              <li key={invite.id}>
                <span>
                  {invite.display_name_hint ?? "Unnamed invite"} • {invite.role_to_grant} •{" "}
                  {invite.claimed_at ? "Claimed" : invite.revoked_at ? "Revoked" : "Active"}
                </span>
                {!invite.revoked_at && !invite.claimed_at ? (
                  <button
                    className="book-card__button book-card__button--ghost"
                    onClick={() => void handleRevokeInvite(invite.id)}
                    type="button"
                  >
                    Revoke
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
