import { useEffect, useRef } from "react";
import type { PublicTurn } from "../../types/chat";
import { AssistantAnswerCard } from "../chat/AssistantAnswerCard";
import { UserBubble } from "../chat/UserBubble";

interface MessageListProps {
  turns: PublicTurn[];
}

function renderTurn(turn: PublicTurn) {
  if (turn.role === "user") {
    return <UserBubble key={turn.id} turn={turn} />;
  }

  return <AssistantAnswerCard key={turn.id} turn={turn} />;
}

export function MessageList({ turns }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (turns.length > 0 && typeof bottomRef.current?.scrollIntoView === "function") {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [turns.length]);

  return (
    <section className="message-list" aria-label="对话线程">
      {turns.map(renderTurn)}
      <div ref={bottomRef} />
    </section>
  );
}
