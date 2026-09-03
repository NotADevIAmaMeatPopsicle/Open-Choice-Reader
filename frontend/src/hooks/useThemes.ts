import { useEffect, useState } from "react";

import { listThemes } from "../api/client";
import type { ThemeProfileRecord } from "../api/types";

type UseThemesResult = {
  error: string | null;
  isLoading: boolean;
  refreshThemes: () => Promise<ThemeProfileRecord[]>;
  themes: ThemeProfileRecord[];
};

export function useThemes(): UseThemesResult {
  const [themes, setThemes] = useState<ThemeProfileRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function loadThemes(): Promise<ThemeProfileRecord[]> {
    setIsLoading(true);

    try {
      const loadedThemes = await listThemes();
      setThemes(loadedThemes);
      setError(null);
      return loadedThemes;
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Unable to load themes";
      setError(message);
      throw loadError instanceof Error ? loadError : new Error(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    void loadThemes().catch(() => {
      if (!isMounted) {
        return;
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  return {
    error,
    isLoading,
    refreshThemes: loadThemes,
    themes,
  };
}
