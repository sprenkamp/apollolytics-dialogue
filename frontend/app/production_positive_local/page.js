"use client";

import DialogueChatConfigurable from "../components/DialogueChatConfigurable";
import prompts from "../utils/prompts.json";

export default function PositiveConversationLocalPage() {
  const websocketUrl = "ws://localhost:8000/ws/conversation";
  const promptConfig = prompts.positive;
  
  return <DialogueChatConfigurable websocketUrl={websocketUrl} promptConfig={promptConfig} />;
}
