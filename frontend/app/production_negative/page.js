"use client";

import DialogueChatConfigurable from "../components/DialogueChatConfigurable";
import prompts from "../utils/prompts.json";

export default function NegativeConversationPage() {
  const websocketUrl = "wss://21b5-16-170-227-168.ngrok-free.app/ws/conversation";
  const promptConfig = prompts.negative;
  
  return <DialogueChatConfigurable websocketUrl={websocketUrl} promptConfig={promptConfig} />;
}