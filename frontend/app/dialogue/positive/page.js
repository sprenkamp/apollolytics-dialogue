"use client";

import DialogueChatConfigurable from "../../components/DialogueChatConfigurable";
import prompts from "../../utils/prompts.json";
import config from "../../utils/config";

export default function PositiveConversationPage() {
  const websocketUrl = config.getWebsocketUrl();
  const promptConfig = prompts.positive;
  
  return <DialogueChatConfigurable websocketUrl={websocketUrl} promptConfig={promptConfig} />;
}