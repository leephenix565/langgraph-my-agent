import type { ReactNode } from "react";

interface WorkflowSectionProps {
  eyebrow: string;
  title: string;
  icon: string;
  isLast?: boolean;
  children: ReactNode;
}

export function WorkflowSection({ eyebrow, title, icon, isLast = false, children }: WorkflowSectionProps) {
  const showEyebrow = eyebrow && eyebrow !== title;

  return (
    <section className="workflow-section">
      <div className="workflow-section__rail" aria-hidden="true">
        <div className="workflow-section__node">{icon}</div>
        {!isLast ? <div className="workflow-section__line" /> : null}
      </div>
      <div className="workflow-section__card">
        <header className="workflow-section__header">
          {showEyebrow ? <span className="workflow-section__eyebrow">{eyebrow}</span> : null}
          <h4>{title}</h4>
        </header>
        {children}
      </div>
    </section>
  );
}
