import type { PublicTurn } from "../../types/chat";
import { getStructuredInputSections, parseStructuredUserTurn } from "../../utils/structuredInput";

interface UserBubbleProps {
  turn: PublicTurn;
}

export function UserBubble({ turn }: UserBubbleProps) {
  const typedSections = turn.structuredInput ? getStructuredInputSections(turn.structuredInput) : [];
  const parsed = typedSections.length ? null : parseStructuredUserTurn(turn.text);
  const structuredSections = typedSections.length ? typedSections : parsed?.sections ?? [];

  return (
    <article
      className={`turn turn--user${structuredSections.length ? " turn--structured" : ""}`}
      aria-label="用户消息"
    >
      <div className="turn__meta">{turn.createdAt}</div>
      {structuredSections.length ? (
        <div className="turn__structured" aria-label="结构化输入">
          {structuredSections.map((section) => (
            <section className="turn__section" key={section.key}>
              <span className="turn__section-label">{section.title}</span>
              {section.items?.length ? (
                <ol
                  className={`turn__section-list${section.key === "urlReferences" ? " turn__section-list--links" : ""}`}
                >
                  {section.items.map((item, index) => (
                    <li className="turn__section-item" key={`${section.key}-${index}`}>
                      <span className="turn__section-item-label">
                        {section.key === "urlReferences" ? `链接 ${index + 1}` : `材料 ${index + 1}`}
                      </span>
                      {section.key === "urlReferences" ? (
                        <a className="turn__section-link" href={item} target="_blank" rel="noreferrer">
                          {item}
                        </a>
                      ) : (
                        <p className="turn__section-value">{item}</p>
                      )}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="turn__section-value">{section.value}</p>
              )}
            </section>
          ))}
        </div>
      ) : (
        <p className="turn__text">{turn.text}</p>
      )}
    </article>
  );
}
