import type { FinalSource } from "../../types/chat";
import { sourceLabel } from "../../content/zh-CN";

interface SourceBadgeProps {
  source: FinalSource;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  return (
    <span className={`source-badge source-badge--${source}`}>
      <span className="source-badge__dot" aria-hidden="true" />
      {sourceLabel(source)}
    </span>
  );
}
