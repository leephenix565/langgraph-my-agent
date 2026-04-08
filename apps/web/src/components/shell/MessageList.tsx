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
  return (
    <section className="message-list" aria-label="对话线程">
      {turns.map(renderTurn)}
    </section>
  );
}
