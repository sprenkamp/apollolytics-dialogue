// app/production/page.js
"use client";
import ChatTemplate from "../components/ChatTemplate";

export default function Production() {
  return (
    <ChatTemplate
      predefinedArticle={null}
      allowArticleInput={true}
      title="Apollolytics Dialogue - Production"
      dialogueType="socratic" // Set to "socratic" for the good bot
      useFakeData={false}     // Use real data in production
    />
  );
}
