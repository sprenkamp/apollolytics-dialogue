// components/ChatTemplate.js
"use client";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import styles from "../Home.module.css"; // Ensure this path is correct

export default function ChatTemplate({
  predefinedArticle = null,
  allowArticleInput = false,
  title,
  dialogueType = "socratic", // New prop for dialogue_type
  useFakeData = false, // Existing prop
}) {
  const [conversation, setConversation] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [article, setArticle] = useState(predefinedArticle || "");
  const [loading, setLoading] = useState(false);
  const [articleSubmitted, setArticleSubmitted] = useState(false);
  const chatWindowRef = useRef(null);

  // Set the backendUrl inside the component
  const backendUrl = "https://duly-fresh-alien.ngrok-free.app";

  // Handles article submission
  const handleArticleSubmit = async (e) => {
    e.preventDefault();
    if (!article.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(
        `${backendUrl}/analyze_propaganda`, // Unified endpoint
        {
          article_text: article,
          dialogue_type: dialogueType, // Use the dialogueType prop
          use_fake_data: useFakeData,   // Include useFakeData prop
        },
        {
          withCredentials: true,
        }
      );

      if (response.status === 200) {
        const result = response.data;
        setConversation((prev) => [
          ...prev,
          { sender: "bot", message: result.bot_message },
        ]);
        setArticleSubmitted(true);
      } else {
        setConversation((prev) => [
          ...prev,
          {
            sender: "bot",
            message: "Error: Failed to analyze the article.",
          },
        ]);
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        {
          sender: "bot",
          message: "Error: Unable to communicate with the server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handles user message submission
  const handleUserMessageSubmit = async (e) => {
    e.preventDefault();
    if (!userMessage.trim() || !articleSubmitted) return;

    // Display the user message immediately
    setConversation((prev) => [
      ...prev,
      { sender: "user", message: userMessage },
    ]);
    setUserMessage(""); // Clear user input
    setLoading(true);

    try {
      const response = await axios.post(
        `${backendUrl}/continue_conversation`, // Continue conversation endpoint
        {
          user_input: userMessage,
        },
        {
          withCredentials: true,
        }
      );

      if (response.status === 200) {
        const botResponse = response.data.bot_message;
        setConversation((prev) => [
          ...prev,
          { sender: "bot", message: botResponse },
        ]);
      } else {
        setConversation((prev) => [
          ...prev,
          {
            sender: "bot",
            message: "Error: Failed to process your message.",
          },
        ]);
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        {
          sender: "bot",
          message: "Error: Unable to communicate with the server.",
        },
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
      <h1 className={styles.header}>{title}</h1>

      {/* Article Submission Form */}
      {!articleSubmitted && (
        <form onSubmit={handleArticleSubmit} className={styles.inputForm}>
          {allowArticleInput ? (
            <textarea
              value={article}
              onChange={(e) => setArticle(e.target.value)}
              placeholder="Enter your article here..."
              className={styles.inputField}
              required
            />
          ) : (
            <textarea
              value={article}
              readOnly
              className={styles.inputField}
              rows={10}
            />
          )}
          <button
            type="submit"
            className={styles.sendButton}
            disabled={loading}
          >
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
        {loading && (
          <div className={styles.loadingSpinner}>
            <div className={styles.spinner}></div>
          </div>
        )}
      </div>

      {/* User message input */}
      {articleSubmitted && (
        <form
          onSubmit={handleUserMessageSubmit}
          className={styles.inputForm}
        >
          <input
            type="text"
            placeholder="Continue the conversation..."
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            className={styles.inputField}
            disabled={loading}
          />
          <button
            type="submit"
            className={styles.sendButton}
            disabled={loading}
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      )}
    </div>
  );
}
