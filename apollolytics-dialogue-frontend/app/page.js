"use client";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import styles from "./Home.module.css"; // Import the CSS module

export default function Home() {
  const [conversation, setConversation] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [article, setArticle] = useState(""); // Separate state for article input
  const [loading, setLoading] = useState(false);
  const [articleSubmitted, setArticleSubmitted] = useState(false);
  const [detectedPropaganda, setDetectedPropaganda] = useState(null);
  const chatWindowRef = useRef(null); // Ref for auto-scrolling
  const backendUrl = 'https://16.170.227.168:8000';  // Use your EC2 instance IP

  // Handles article submission
  const handleArticleSubmit = async (e) => {
    e.preventDefault();
    if (!article.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(
        `${backendUrl}/analyze_propaganda`,
        {
          article_text: article,
        },
        {
          withCredentials: true, // Important: Ensures cookies are sent
        }
      );

      if (response.status === 200) {
        const result = response.data;
        setDetectedPropaganda(result.detected_propaganda); // Save detected propaganda
        setConversation((prev) => [
          ...prev,
          { sender: "bot", message: result.bot_message }, // Bot responds first
        ]);
        setArticleSubmitted(true); // Mark that the article was submitted
      } else {
        setConversation((prev) => [
          ...prev,
          { sender: "bot", message: "Error: Failed to analyze the article." },
        ]);
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        { sender: "bot", message: "Error: Unable to communicate with the server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handles user message submission
  const handleUserMessageSubmit = async (e) => {
    e.preventDefault();
    if (!userMessage.trim() || !articleSubmitted) return; // Prevent submission if no article was submitted

    setLoading(true);
    try {
      const response = await axios.post(
        `${backendUrl}/continue_conversation`, // Use backendUrl variable
        {
          user_input: userMessage,
        },
        {
          withCredentials: true, // Important: Ensures cookies are sent
        }
      );

      if (response.status === 200) {
        const botResponse = response.data.bot_message;
        setConversation((prev) => [
          ...prev,
          { sender: "user", message: userMessage }, // User's message
          { sender: "bot", message: botResponse }, // Bot's response
        ]);
        setUserMessage(''); // Clear user input
      } else {
        setConversation((prev) => [
          ...prev,
          { sender: "bot", message: "Error: Failed to process your message." },
        ]);
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        { sender: "bot", message: "Error: Unable to communicate with the server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-scroll to the bottom of the chat window whenever a new message is added
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [conversation]);

  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Apollolytics Dialogue</h1>

      {/* Article submission */}
      {!articleSubmitted && (
        <form onSubmit={handleArticleSubmit} className={styles.inputForm}>
          <textarea
            placeholder="Submit your article for propaganda detection..."
            value={article}
            onChange={(e) => setArticle(e.target.value)}
            className={styles.inputField}
          />
          <button type="submit" className={styles.sendButton} disabled={loading}>
            {loading ? "Analyzing..." : "Submit Article"}
          </button>
        </form>
      )}

      {/* Chat Window */}
      <div ref={chatWindowRef} className={styles.chatWindow}>
        {conversation.map((chat, index) => (
          <div
            key={index}
            className={`${styles.messageBubble} ${
              chat.sender === "user" ? styles.userMessage : styles.botMessage
            }`}
          >
            <span>{chat.message}</span>
          </div>
        ))}
      </div>

      {/* User message input */}
      {articleSubmitted && (
        <form onSubmit={handleUserMessageSubmit} className={styles.inputForm}>
          <input
            type="text"
            placeholder="Continue the conversation..."
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            className={styles.inputField}
          />
          <button type="submit" className={styles.sendButton} disabled={loading}>
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      )}
    </div>
  );
}
