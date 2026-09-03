import type { FormEvent } from "react";
import { useEffect, useState } from "react";

type ClaimInvitePageProps = {
  error: string | null;
  initialToken?: string | null;
  isSubmitting: boolean;
  onBackToLogin: () => void;
  onClaimInvite: (payload: { token: string; username: string; display_name?: string; password: string }) => Promise<void>;
};

export function ClaimInvitePage({
  error,
  initialToken,
  isSubmitting,
  onBackToLogin,
  onClaimInvite,
}: ClaimInvitePageProps) {
  const [token, setToken] = useState(initialToken ?? "");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    setToken(initialToken ?? "");
  }, [initialToken]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onClaimInvite({
        token: token.trim(),
        username: username.trim(),
        display_name: displayName.trim() || undefined,
        password,
      });
    } catch (submitFailure) {
      setSubmitError(submitFailure instanceof Error ? submitFailure.message : "Unable to claim invite");
    }
  };

  return (
    <section aria-label="Claim invite page" className="auth-page">
      <div className="auth-page__card">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Invite-only access</p>
          <h2>Claim an account invite</h2>
          <p>Use the invite token from the household admin to create your local Open Choice Reader account.</p>
        </div>

        {error ? <p className="library-page__alert" role="alert">{error}</p> : null}
        {submitError ? <p className="library-page__alert" role="alert">{submitError}</p> : null}

        <form className="auth-page__form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="library-page__field">
            <span>Invite token</span>
            <textarea onChange={(event) => setToken(event.target.value)} rows={3} value={token} />
          </label>
          <label className="library-page__field">
            <span>Username</span>
            <input onChange={(event) => setUsername(event.target.value)} type="text" value={username} />
          </label>
          <label className="library-page__field">
            <span>Display name</span>
            <input onChange={(event) => setDisplayName(event.target.value)} type="text" value={displayName} />
          </label>
          <label className="library-page__field">
            <span>Password</span>
            <input onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
          </label>
          <div className="auth-page__actions">
            <button
              className="book-card__button"
              disabled={isSubmitting || !token.trim() || !username.trim() || !password}
              type="submit"
            >
              {isSubmitting ? "Claiming invite..." : "Claim invite"}
            </button>
            <button className="book-card__button book-card__button--ghost" onClick={onBackToLogin} type="button">
              Back to login
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
