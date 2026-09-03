import type { ReactNode } from "react";

import { IconGlyph } from "./IconGlyph";

type EmptyStateProps = {
  action?: ReactNode;
  copy: string;
  icon?: Parameters<typeof IconGlyph>[0]["name"];
  title: string;
};

export function EmptyState({ action, copy, icon = "book", title }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <span aria-hidden="true" className="empty-state__icon">
        <IconGlyph name={icon} />
      </span>
      <p className="empty-state__title">{title}</p>
      <p className="empty-state__copy">{copy}</p>
      {action ?? null}
    </div>
  );
}
