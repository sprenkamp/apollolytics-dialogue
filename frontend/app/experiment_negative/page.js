"use client";
import ChatTemplate from "../components/ChatTemplate";
import predefinedArticle from "../utils/articleText";

export default function Production() {
  return (
    <ChatTemplate
      predefinedArticle={predefinedArticle}
      allowArticleInput={false}
      title="Apollolytics Dialogue - Experiment"
      dialogueType="negative-socratic" // Set to "socratic" for the good bot
      useFakeData={true}     // Use real data in production
    />
  );
}
