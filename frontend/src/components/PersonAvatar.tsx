type PersonAvatarProps = {
  displayName: string;
};

export function personInitials(displayName: string) {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  const initials = parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return initials || "?";
}

export function PersonAvatar({ displayName }: PersonAvatarProps) {
  return (
    <span aria-hidden="true" className="person-avatar">
      {personInitials(displayName)}
    </span>
  );
}
