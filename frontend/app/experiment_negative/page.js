// app/production/page.js
"use client";
import ChatTemplate from "../components/ChatTemplate";
import predefinedArticle from "../utils/articleText";

export default function Production() {
  return (
    <ChatTemplate
      predefinedArticle={predefinedArticle}
      allowArticleInput={true}
      title="Apollolytics Dialogue - Experiment"
      dialogueType="negative-socratic" // Set to "socratic" for the good bot
      useFakeData={false}     // Use real data in production
    />
  );
}
