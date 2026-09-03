import type { FormEvent } from "react";
import { useState } from "react";

import type { BootstrapAdminPayload } from "../api/types";

type BootstrapAdminPageProps = {
  error: string | null;
  isSubmitting: boolean;
  onBootstrap: (payload: BootstrapAdminPayload) => Promise<void>;
};

export function BootstrapAdminPage({ error, isSubmitting, onBootstrap }: BootstrapAdminPageProps) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    try {
      await onBootstrap({
        username: username.trim(),
        display_name: displayName.trim() || undefined,
        password,
        bootstrap_token: bootstrapToken.trim() || undefined,
      });
    } catch (submitFailure) {
      setSubmitError(submitFailure instanceof Error ? submitFailure.message : "Unable to create the first admin account");
    }
  };

  return (
    <section aria-label="Bootstrap admin page" className="auth-page">
      <div className="auth-page__card">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">First run</p>
          <h2>Create the first admin account</h2>
          <p>Open Choice Reader needs one local administrator before invite-only household accounts can sign in.</p>
        </div>

        {error ? <p className="library-page__alert" role="alert">{error}</p> : null}
        {submitError ? <p className="library-page__alert" role="alert">{submitError}</p> : null}

        <form className="auth-page__form" onSubmit={(event) => void handleSubmit(event)}>
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
          <label className="library-page__field">
            <span>Setup token (remote setup only)</span>
            <input
              autoComplete="one-time-code"
              onChange={(event) => setBootstrapToken(event.target.value)}
              type="password"
              value={bootstrapToken}
            />
          </label>
          <div className="auth-page__actions">
            <button className="book-card__button" disabled={isSubmitting || !username.trim() || !password} type="submit">
              {isSubmitting ? "Creating admin..." : "Create admin"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
