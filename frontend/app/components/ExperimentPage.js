"use client";

import { useState } from 'react';
import ProlificIDInput from './ProlificIDInput';
import DialogueChatConfigurable from './DialogueChatConfigurable';

export default function ExperimentPage({ 
  title, 
  article, 
  websocketUrl, 
  promptConfig 
}) {
  const [prolificId, setProlificId] = useState(null);

  const handleProlificIdSubmit = (id) => {
    setProlificId(id);
  };

  if (!prolificId) {
    return <ProlificIDInput onSubmit={handleProlificIdSubmit} />;
  }

  return (
    <div className="experiment-container">
      <h1 className="title">{title}</h1>
      <DialogueChatConfigurable 
        websocketUrl={websocketUrl}
        promptConfig={promptConfig}
        initialArticle={article}
        prolificId={prolificId}
      />
    </div>
  );
} 