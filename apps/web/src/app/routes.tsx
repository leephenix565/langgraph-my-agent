import { Route, Routes } from "react-router-dom";
import { AgentsPage } from "../pages/AgentsPage";
import { ChatPage } from "../pages/ChatPage";
import { SettingsPage } from "../pages/SettingsPage";
import type { ApiError } from "../services/api";
import type { ChatSessionSummary, HealthResponse, PublicTurn, RoutingRequestModel, StructuredInputModel } from "../types/chat";

export interface AppRoutesProps {
  activeSession: ChatSessionSummary | null;
  activeTurns: PublicTurn[];
  onSendMessage: (value: string, structuredInput?: StructuredInputModel, routing?: RoutingRequestModel | null) => void;
  onClearMessages: () => void;
  isLoading: boolean;
  isSending: boolean;
  isClearing: boolean;
  unavailable: boolean;
  degraded: boolean;
  errorMessage: string | null;
  errorMeta: ApiError | null;
  health: HealthResponse | null;
}

export function AppRoutes({
  activeSession,
  activeTurns,
  onSendMessage,
  onClearMessages,
  isLoading,
  isSending,
  isClearing,
  unavailable,
  degraded,
  errorMessage,
  errorMeta,
  health,
}: AppRoutesProps) {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ChatPage
            session={activeSession}
            turns={activeTurns}
            onSendMessage={onSendMessage}
            onClearMessages={onClearMessages}
            isLoading={isLoading}
            isSending={isSending}
            isClearing={isClearing}
            unavailable={unavailable}
            degraded={degraded}
            errorMessage={errorMessage}
            errorMeta={errorMeta}
            health={health}
          />
        }
      />
      <Route path="/agents" element={<AgentsPage />} />
      <Route path="/settings" element={<SettingsPage health={health} isLoading={isLoading} unavailable={unavailable} />} />
    </Routes>
  );
}
