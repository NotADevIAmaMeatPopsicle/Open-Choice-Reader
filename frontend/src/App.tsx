import { useEffect, useState } from "react";

import { ProtectedApp } from "./components/ProtectedApp";
import { useAuth } from "./hooks/useAuth";
import { setPlayerStorageUserScope } from "./hooks/usePlayer";
import type { BootstrapAdminPayload } from "./api/types";
import { BootstrapAdminPage } from "./routes/BootstrapAdminPage";
import { ClaimInvitePage } from "./routes/ClaimInvitePage";
import { LoginPage } from "./routes/LoginPage";
import { PlayerWindowPage } from "./routes/PlayerWindowPage";

function readPathname() {
  return window.location.pathname;
}

function readSearch() {
  return window.location.search;
}

function readLoginNotice(search: string) {
  const reason = new URLSearchParams(search).get("reason");
  if (reason === "extension-auth-required") {
    return "Sign in to Open Choice Reader on this host first, then try the extension again.";
  }

  return null;
}

export default function App() {
  const [pathname, setPathname] = useState(readPathname);
  const [search, setSearch] = useState(readSearch);
  const [authActionError, setAuthActionError] = useState<string | null>(null);
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false);
  const { bootstrapAvailable, currentUser, error, isLoading, bootstrapAdmin, claimInvite, login, logout } = useAuth();

  useEffect(() => {
    const handleLocationChange = () => {
      setPathname(readPathname());
      setSearch(readSearch());
    };

    window.addEventListener("popstate", handleLocationChange);

    return () => {
      window.removeEventListener("popstate", handleLocationChange);
    };
  }, []);

  useEffect(() => {
    setPlayerStorageUserScope(currentUser?.id ?? null);
  }, [currentUser?.id]);

  const navigateTo = (nextPathname: string) => {
    window.history.pushState({}, "", nextPathname);
    setPathname(nextPathname);
    setSearch(window.location.search);
  };

  if (pathname.startsWith("/player/")) {
    return <PlayerWindowPage onNavigate={navigateTo} sessionId={pathname.split("/")[2] ?? "1"} />;
  }

  const claimToken = new URLSearchParams(search).get("token");
  const loginNotice = readLoginNotice(search);

  const handleBootstrapAdmin = async (payload: BootstrapAdminPayload) => {
    setAuthActionError(null);
    setIsSubmittingAuth(true);
    try {
      await bootstrapAdmin(payload);
      navigateTo("/");
    } catch (submitError) {
      setAuthActionError(submitError instanceof Error ? submitError.message : "Unable to create admin account");
      throw submitError;
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  const handleLogin = async (payload: { username: string; password: string }) => {
    setAuthActionError(null);
    setIsSubmittingAuth(true);
    try {
      await login(payload);
      navigateTo("/");
    } catch (submitError) {
      setAuthActionError(submitError instanceof Error ? submitError.message : "Unable to sign in");
      throw submitError;
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  const handleClaimInvite = async (payload: { token: string; username: string; display_name?: string; password: string }) => {
    setAuthActionError(null);
    setIsSubmittingAuth(true);
    try {
      await claimInvite(payload);
      navigateTo("/");
    } catch (submitError) {
      setAuthActionError(submitError instanceof Error ? submitError.message : "Unable to claim invite");
      throw submitError;
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  const handleLogout = async () => {
    setAuthActionError(null);
    await logout();
    navigateTo("/login");
  };

  if (isLoading) {
    return (
      <section aria-label="Loading account session" className="library-page settings-page">
        <p className="library-page__status-copy">Loading account session...</p>
      </section>
    );
  }

  if (bootstrapAvailable) {
    return <BootstrapAdminPage error={error ?? authActionError} isSubmitting={isSubmittingAuth} onBootstrap={handleBootstrapAdmin} />;
  }

  if (!currentUser) {
    if (pathname === "/claim-invite") {
      return (
        <ClaimInvitePage
          error={error ?? authActionError}
          initialToken={claimToken}
          isSubmitting={isSubmittingAuth}
          onBackToLogin={() => navigateTo("/login")}
          onClaimInvite={handleClaimInvite}
        />
      );
    }

    return (
      <LoginPage
        error={error ?? authActionError}
        isSubmitting={isSubmittingAuth}
        notice={loginNotice}
        onClaimInvite={() => navigateTo("/claim-invite")}
        onLogin={handleLogin}
      />
    );
  }

  return <ProtectedApp currentPathname={pathname} currentUser={currentUser} onLogout={handleLogout} onNavigate={navigateTo} />;
}
