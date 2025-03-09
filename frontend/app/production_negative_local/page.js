"use client";

import DialogueChatConfigurable from "../components/DialogueChatConfigurable";
import prompts from "../utils/prompts.json";

export default function NegativeConversationLocalPage() {
  const websocketUrl = "ws://localhost:8000/ws/conversation";
  const promptConfig = prompts.negative;
  
  return <DialogueChatConfigurable websocketUrl={websocketUrl} promptConfig={promptConfig} />;
}