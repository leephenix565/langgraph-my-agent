import { useId, useState } from "react";
import type { WorkflowModel } from "../../types/workflow";
import { WorkflowPanel } from "./WorkflowPanel";

interface TechnicalWorkflowDisclosureProps {
  workflow: WorkflowModel;
}

export function TechnicalWorkflowDisclosure({ workflow }: TechnicalWorkflowDisclosureProps) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();

  return (
    <section className="technical-workflow" aria-label="技术流程详情">
      <button
        type="button"
        className="technical-workflow__toggle"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={() => setExpanded((current) => !current)}
      >
        <span className="technical-workflow__copy">
          <span className="technical-workflow__mark" aria-hidden="true">
            DAG
          </span>
          <span>
            <strong>技术流程详情</strong>
            <span>查看完整 DAG 步骤、批次、运行元数据与溯源信息</span>
          </span>
        </span>
        <span className="technical-workflow__action">{expanded ? "收起技术详情" : "展开技术详情"}</span>
      </button>

      {expanded ? (
        <div className="technical-workflow__content" id={contentId}>
          <WorkflowPanel workflow={workflow} defaultExpanded />
        </div>
      ) : null}
    </section>
  );
}
