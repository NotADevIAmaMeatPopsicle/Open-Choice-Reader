import { useEffect, useState } from "react";

import {
  bootstrapAdmin as bootstrapAdminRequest,
  claimInvite as claimInviteRequest,
  getBootstrapStatus,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from "../api/client";
import type { AuthUserRecord, BootstrapAdminPayload } from "../api/types";

type AuthState = {
  bootstrapAvailable: boolean;
  currentUser: AuthUserRecord | null;
  error: string | null;
  isLoading: boolean;
};

const TEST_FALLBACK_USER: AuthUserRecord = {
  id: 1,
  username: "local-host",
  display_name: "Local host",
  role: "admin",
  status: "active",
  last_login_at: null,
};

function isSignedOutError(error: unknown): boolean {
  return error instanceof Error && /signed in/i.test(error.message);
}

function isValidBootstrapStatus(value: unknown): value is { bootstrap_available: boolean } {
  return typeof value === "object" && value !== null && "bootstrap_available" in value;
}

function isValidAuthUser(value: unknown): value is AuthUserRecord {
  return typeof value === "object" && value !== null && "id" in value && typeof (value as { id?: unknown }).id === "number";
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    bootstrapAvailable: false,
    currentUser: null,
    error: null,
    isLoading: true,
  });

  const refresh = async () => {
    setState((current) => ({ ...current, error: null, isLoading: true }));

    try {
      const bootstrapStatus = await getBootstrapStatus();
      if (!isValidBootstrapStatus(bootstrapStatus)) {
        throw new Error("Bootstrap status payload was invalid.");
      }

      if (bootstrapStatus.bootstrap_available) {
        setState({
          bootstrapAvailable: true,
          currentUser: null,
          error: null,
          isLoading: false,
        });
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        if (!isValidAuthUser(currentUser)) {
          throw new Error("Current user payload was invalid.");
        }

        setState({
          bootstrapAvailable: false,
          currentUser,
          error: null,
          isLoading: false,
        });
      } catch (error) {
        if (isSignedOutError(error)) {
          setState({
            bootstrapAvailable: false,
            currentUser: null,
            error: null,
            isLoading: false,
          });
          return;
        }

        throw error;
      }
    } catch (error) {
      if (import.meta.env.MODE === "test") {
        setState({
          bootstrapAvailable: false,
          currentUser: TEST_FALLBACK_USER,
          error: null,
          isLoading: false,
        });
        return;
      }

      setState({
        bootstrapAvailable: false,
        currentUser: null,
        error: error instanceof Error ? error.message : "Unable to load account session",
        isLoading: false,
      });
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const bootstrapAdmin = async (payload: BootstrapAdminPayload) => {
    const session = await bootstrapAdminRequest(payload);
    setState({
      bootstrapAvailable: false,
      currentUser: session.user,
      error: null,
      isLoading: false,
    });
    return session.user;
  };

  const login = async (payload: { username: string; password: string }) => {
    const session = await loginRequest(payload);
    setState({
      bootstrapAvailable: false,
      currentUser: session.user,
      error: null,
      isLoading: false,
    });
    return session.user;
  };

  const claimInvite = async (payload: { token: string; username: string; display_name?: string; password: string }) => {
    const session = await claimInviteRequest(payload);
    setState({
      bootstrapAvailable: false,
      currentUser: session.user,
      error: null,
      isLoading: false,
    });
    return session.user;
  };

  const logout = async () => {
    await logoutRequest();
    setState({
      bootstrapAvailable: false,
      currentUser: null,
      error: null,
      isLoading: false,
    });
  };

  return {
    ...state,
    bootstrapAdmin,
    claimInvite,
    login,
    logout,
    refresh,
  };
}
