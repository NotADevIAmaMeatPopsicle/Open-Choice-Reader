type IconName =
  | "home"
  | "discover"
  | "library"
  | "series"
  | "collections"
  | "issues"
  | "jobs"
  | "voices"
  | "themes"
  | "settings"
  | "dashboard"
  | "queue"
  | "user"
  | "logout"
  | "search"
  | "backward"
  | "forward"
  | "play"
  | "pause"
  | "book"
  | "chevron-left"
  | "chevron-right"
  | "speaker"
  | "popout"
  | "friends"
  | "admin"
  | "seek-back-5"
  | "seek-back-30"
  | "seek-forward-5"
  | "seek-forward-30";

type IconGlyphProps = {
  name: IconName;
};

const SEEK_BACK_ARC = "M3.5 4v4.5H8M3.5 12a8.5 8.5 0 1 0 8.5-8.5 9.2 9.2 0 0 0-6.4 2.6L3.5 8.5";
const SEEK_FORWARD_ARC = "M20.5 4v4.5H16M20.5 12a8.5 8.5 0 1 1-8.5-8.5 9.2 9.2 0 0 1 6.4 2.6l2.1 2.4";

const SEEK_GLYPHS: Partial<Record<IconName, { arc: string; label: string }>> = {
  "seek-back-5": { arc: SEEK_BACK_ARC, label: "5" },
  "seek-back-30": { arc: SEEK_BACK_ARC, label: "30" },
  "seek-forward-5": { arc: SEEK_FORWARD_ARC, label: "5" },
  "seek-forward-30": { arc: SEEK_FORWARD_ARC, label: "30" },
};

function iconPath(name: IconName) {
  switch (name) {
    case "home":
      return "M4 10.5 12 4l8 6.5v8a1 1 0 0 1-1 1h-4.5v-5h-5v5H5a1 1 0 0 1-1-1z";
    case "discover":
      return "M12 4.5a7.5 7.5 0 1 0 7.5 7.5A7.5 7.5 0 0 0 12 4.5zm0 0v7.5l4 2.3";
    case "library":
      return "M5 5h11a2 2 0 0 1 2 2v11H8a3 3 0 0 0-3 3zm13 0h1a2 2 0 0 1 2 2v13H8a2 2 0 0 1 2-2h8z";
    case "series":
      return "M6 6h12v3H6zm0 5h12v3H6zm0 5h12v3H6z";
    case "collections":
      return "M5 7h14v11H5zM7 5h10v2H7zm2-2h6v2H9z";
    case "issues":
      return "M12 5.5 19 18H5zm0 4v3.5m0 3h.01";
    case "jobs":
      return "M6 18h3V9H6zm5 0h3V5h-3zm5 0h3v-7h-3z";
    case "voices":
      return "M12 5a3 3 0 0 1 3 3v3a3 3 0 0 1-6 0V8a3 3 0 0 1 3-3zm-5 6a5 5 0 0 0 10 0m-5 5v3m-3 0h6";
    case "themes":
      return "M12 4.5 18 8v8l-6 3.5L6 16V8zm0 0L6 8l6 3.5L18 8";
    case "settings":
      return "M12 8.5A3.5 3.5 0 1 1 8.5 12 3.5 3.5 0 0 1 12 8.5zm0-4 1.4 1.2 1.8-.3.8 1.6 1.8.7-.2 1.8 1.2 1.4-1.2 1.4.2 1.8-1.8.7-.8 1.6-1.8-.3L12 19.5l-1.4-1.2-1.8.3-.8-1.6-1.8-.7.2-1.8L5.3 12l1.2-1.4-.2-1.8 1.8-.7.8-1.6 1.8.3z";
    case "dashboard":
      return "M5 14h4v5H5zm5-9h4v14h-4zm5 4h4v10h-4z";
    case "queue":
      return "M5 7h10v2H5zm0 5h10v2H5zm0 5h10v2H5zm12-9h2v2h-2zm0 5h2v2h-2z";
    case "user":
      return "M12 12a3.5 3.5 0 1 0-3.5-3.5A3.5 3.5 0 0 0 12 12zm0 2c-3.3 0-6 1.8-6 4v1h12v-1c0-2.2-2.7-4-6-4z";
    case "logout":
      return "M9 6H6.5A1.5 1.5 0 0 0 5 7.5v9A1.5 1.5 0 0 0 6.5 18H9m4-9h7m0 0-3-3m3 3-3 3";
    case "search":
      return "M11 5a6 6 0 1 0 3.9 10.6l3 3 1.4-1.4-3-3A6 6 0 0 0 11 5zm0 2a4 4 0 1 1-4 4 4 4 0 0 1 4-4z";
    case "backward":
      return "M11.5 7 6 12l5.5 5V7zm6 0L12 12l5.5 5V7z";
    case "forward":
      return "m12.5 7 5.5 5-5.5 5V7zm-6 0 5.5 5-5.5 5V7z";
    case "play":
      return "M8 6.5v11l9-5.5z";
    case "pause":
      return "M8 6h3v12H8zm5 0h3v12h-3z";
    case "book":
      return "M6 5h10a2 2 0 0 1 2 2v12H8a3 3 0 0 0-2 3zm12 0h1a2 2 0 0 1 2 2v13H8a2 2 0 0 1 2-2h8z";
    case "chevron-left":
      return "m14.5 6-6 6 6 6";
    case "chevron-right":
      return "m9.5 6 6 6-6 6";
    case "speaker":
      return "M5 10h3.5L13 6.5v11L8.5 14H5zm11 5a5 5 0 0 0 0-10m2 13a9 9 0 0 0 0-16";
    case "popout":
      return "M8 16 16 8m-6 0h6v6";
    case "friends":
      return "M9 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm0 2c-2.8 0-5 1.5-5 3.4V18h10v-1.6c0-1.9-2.2-3.4-5-3.4zm7-2a2.5 2.5 0 1 0-2.5-2.5A2.5 2.5 0 0 0 16 11zm0 2c-.6 0-1.2.1-1.7.3 1 .8 1.7 1.9 1.7 3.1V18h4v-1.4c0-1.8-1.8-3.6-4-3.6z";
    case "admin":
      return "M12 4.5 18.5 7v4.5c0 4-2.8 6.9-6.5 8-3.7-1.1-6.5-4-6.5-8V7zm-2.5 7 1.8 1.8 3.4-3.4";
    default:
      return "M5 12h14";
  }
}

export function IconGlyph({ name }: IconGlyphProps) {
  const seekGlyph = SEEK_GLYPHS[name];

  if (seekGlyph) {
    return (
      <svg aria-hidden="true" className="icon-glyph icon-glyph--seek" fill="none" viewBox="0 0 24 24">
        <path d={seekGlyph.arc} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" />
        <text fill="currentColor" fontSize="10" fontWeight="600" stroke="none" textAnchor="middle" x="12" y="15.5">
          {seekGlyph.label}
        </text>
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" className="icon-glyph" fill="none" viewBox="0 0 24 24">
      <path d={iconPath(name)} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}
