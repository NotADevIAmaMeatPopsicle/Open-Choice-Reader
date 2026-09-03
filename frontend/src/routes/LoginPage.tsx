import type { FormEvent } from "react";
import { useState } from "react";

type LoginPageProps = {
  error: string | null;
  isSubmitting: boolean;
  notice?: string | null;
  onClaimInvite: () => void;
  onLogin: (payload: { username: string; password: string }) => Promise<void>;
};

export function LoginPage({ error, isSubmitting, notice, onClaimInvite, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onLogin({
        username: username.trim(),
        password,
      });
    } catch (submitFailure) {
      setSubmitError(submitFailure instanceof Error ? submitFailure.message : "Unable to sign in");
    }
  };

  return (
    <section aria-label="Login page" className="auth-page">
      <div className="auth-page__card">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Open Choice Reader</p>
          <h2>Sign in to Open Choice Reader</h2>
          <p>Use your local invite-only account to open your library, settings, and reading history.</p>
        </div>

        {notice ? <p className="library-page__status-copy" role="status">{notice}</p> : null}
        {error ? <p className="library-page__alert" role="alert">{error}</p> : null}
        {submitError ? <p className="library-page__alert" role="alert">{submitError}</p> : null}

        <form className="auth-page__form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="library-page__field">
            <span>Username</span>
            <input onChange={(event) => setUsername(event.target.value)} type="text" value={username} />
          </label>
          <label className="library-page__field">
            <span>Password</span>
            <input onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
          </label>
          <div className="auth-page__actions">
            <button className="book-card__button" disabled={isSubmitting || !username.trim() || !password} type="submit">
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
            <button className="book-card__button book-card__button--ghost" onClick={onClaimInvite} type="button">
              Claim invite
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
