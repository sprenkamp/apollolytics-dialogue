"use client";

import DialogueChatConfigurable from "../../components/DialogueChatConfigurable";
import prompts from "../../utils/prompts.json";
import config from "../../utils/config";

export default function PositiveConversationPage() {
  const websocketUrl = config.getWebsocketUrl();
  const promptConfig = prompts.positive;
  
  return (
    <div className="experiment-container">
      <h1 className="title">{promptConfig.title}</h1>
      <DialogueChatConfigurable websocketUrl={websocketUrl} promptConfig={promptConfig} />
    </div>
  );
}