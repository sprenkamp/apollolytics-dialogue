"use client";

import DialogueChat from "../components/DialogueChat";

export default function ConversationPage() {
  const websocketUrl = "wss://21b5-16-170-227-168.ngrok-free.app/ws/conversation";
  
  return <DialogueChat websocketUrl={websocketUrl} />;
}
