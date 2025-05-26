"use client";

import ExperimentPage from '../../components/ExperimentPage';
import config from '../../utils/config';
import { articles } from '../../utils/articles';

const promptConfig = {
  title: "Dialogue Bot Experiment",
  mode: "positive",
  articlePrompt: "Article:"
};

const websocketUrl = config.getWebsocketUrl();

export default function Positive1Page() {
  return (
    <ExperimentPage
      title="Dialogue Bot Experiment"
      article={articles.article1}
      websocketUrl={websocketUrl}
      promptConfig={promptConfig}
    />
  );
} 