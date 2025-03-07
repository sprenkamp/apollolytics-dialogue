"use client";

import DialogueChat from "../components/DialogueChat";

export default function ConversationPage() {
  const websocketUrl = "ws://localhost:8000/ws/conversation";
  
  return <DialogueChat websocketUrl={websocketUrl} />;
}
