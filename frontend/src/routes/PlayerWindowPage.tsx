import { useEffect } from "react";

import { NowPlayingDock } from "../components/NowPlayingDock";
import { activatePlaybackSession } from "../hooks/usePlayer";

type PlayerWindowPageProps = {
  onNavigate: (pathname: string) => void;
  sessionId: string;
};

export function PlayerWindowPage({ onNavigate, sessionId }: PlayerWindowPageProps) {
  useEffect(() => {
    void activatePlaybackSession(sessionId, { autoplay: false });
  }, [sessionId]);

  return (
    <section aria-label="Player window page" className="player-window-page">
      <NowPlayingDock dockPosition="popout" onNavigate={onNavigate} tooltipsEnabled variant="popout" />
    </section>
  );
}
