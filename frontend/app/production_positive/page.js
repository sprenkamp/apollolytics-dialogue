// app/page.js
"use client";
import { useState, useRef, useEffect } from "react"; // Import necessary hooks
import axios from "axios"; // Import axios for HTTP requests
import Link from "next/link";
import styles from "./Home.module.css"; // Reuse existing styles or create new ones

export default function Home() {
  const [conversation, setConversation] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [article, setArticle] = useState(""); // Separate state for article input
  const [loading, setLoading] = useState(false);
  const [articleSubmitted, setArticleSubmitted] = useState(false);
  const [detectedPropaganda, setDetectedPropaganda] = useState(null);
  const chatWindowRef = useRef(null); // Ref for auto-scrolling
  const backendUrl = 'http://16.170.227.168:8000';  // Use your EC2 instance IP

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

    // Add the user's message immediately
    setConversation((prev) => [
      ...prev,
      { sender: "user", message: userMessage },
    ]);
    
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
      <h1 className={styles.header}>Welcome to Apollolytics</h1>
      <div className={styles.linksContainer}>
        <Link href="/production" className={styles.linkButton}>
          Go to Production
        </Link>
        <Link href="/experiment" className={styles.linkButton}>
          Go to Experiment
        </Link>
      </div>

      {/* Article Submission Form */}
      <form onSubmit={handleArticleSubmit} className={styles.form}>
        <textarea
          value={article}
          onChange={(e) => setArticle(e.target.value)}
          placeholder="Enter your article here..."
          className={styles.textarea}
          required
        />
        <button type="submit" className={styles.submitButton} disabled={loading}>
          {loading ? "Analyzing..." : "Submit Article"}
        </button>
      </form>

      {/* Chat Window */}
      {articleSubmitted && (
        <div className={styles.chatContainer} ref={chatWindowRef}>
          {conversation.map((msg, index) => (
            <div
              key={index}
              className={
                msg.sender === "user" ? styles.userMessage : styles.botMessage
              }
            >
              <span>{msg.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* User Message Form */}
      {articleSubmitted && (
        <form onSubmit={handleUserMessageSubmit} className={styles.chatForm}>
          <input
            type="text"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Type your message..."
            className={styles.chatInput}
            required
          />
          <button type="submit" className={styles.sendButton} disabled={loading}>
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      )}
    </div>
  );
}
