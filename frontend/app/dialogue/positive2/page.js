"use client";

import ExperimentPage from '../../components/ExperimentPage';
import config from '../../utils/config';
import { articles } from '../../utils/articles';

const promptConfig = {
  title: "Dialogue Bot Experiment",
  mode: "critical",
  articlePrompt: "Article:"
};

const websocketUrl = config.getWebsocketUrl();

export default function Positive2Page() {
  return (
    <ExperimentPage
      title="Dialogue Bot Experiment"
      article={articles.article2}
      websocketUrl={websocketUrl}
      promptConfig={promptConfig}
    />
  );
} 