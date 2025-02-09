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
  const [article, setArticle] = useState(predefinedArticle || "");
  const [loading, setLoading] = useState(false);
  const [articleSubmitted, setArticleSubmitted] = useState(false);
  const [recording, setRecording] = useState(false);
  const chatWindowRef = useRef(null);
  const recognitionRef = useRef(null);

  // Set the backendUrl inside the component
  const backendUrl = "https://duly-fresh-alien.ngrok-free.app";

  // Setup the Speech Recognition API
  useEffect(() => {
    if (!("SpeechRecognition" in window) && !("webkitSpeechRecognition" in window)) {
      alert("Speech recognition is not supported in your browser.");
    } else {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        handleUserMessageSubmit(transcript);
      };
      recognition.onerror = (event) => {
        console.error("Speech recognition error", event);
        setRecording(false);
      };
      recognitionRef.current = recognition;
    }
  }, []);

  // Function to initiate voice recording
  const startRecording = () => {
    if (recognitionRef.current && !loading) {
      setRecording(true);
      recognitionRef.current.start();
    }
  };

  // Function to handle speaking text via the Speech Synthesis API
  const speakText = (text) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  };

  // Handles article submission (remains via text)
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
        speakText(result.bot_message);
      } else {
        setConversation((prev) => [
          ...prev,
          {
            sender: "bot",
            message: "Error: Failed to analyze the article.",
          },
        ]);
        speakText("Error: Failed to analyze the article.");
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        {
          sender: "bot",
          message: "Error: Unable to communicate with the server.",
        },
      ]);
      speakText("Error: Unable to communicate with the server.");
    } finally {
      setLoading(false);
    }
  };

  // Handles user message submission via voice
  const handleUserMessageSubmit = async (transcriptText) => {
    if (!transcriptText.trim() || !articleSubmitted) return;

    // Display the user message immediately
    setConversation((prev) => [
      ...prev,
      { sender: "user", message: transcriptText },
    ]);
    setLoading(true);

    try {
      const response = await axios.post(
        `${backendUrl}/continue_conversation`, // Continue conversation endpoint
        {
          user_input: transcriptText,
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
        speakText(botResponse);
      } else {
        setConversation((prev) => [
          ...prev,
          {
            sender: "bot",
            message: "Error: Failed to process your message.",
          },
        ]);
        speakText("Error: Failed to process your message.");
      }
    } catch (error) {
      setConversation((prev) => [
        ...prev,
        {
          sender: "bot",
          message: "Error: Unable to communicate with the server.",
        },
      ]);
      speakText("Error: Unable to communicate with the server.");
    } finally {
      setLoading(false);
      setRecording(false);
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

      {/* Voice Interaction Controls */}
      {articleSubmitted && (
        <div className={styles.inputForm}>
          <button
            onClick={startRecording}
            className={styles.sendButton}
            disabled={loading || recording}
          >
            {recording ? "Recording..." : "Start Recording"}
          </button>
        </div>
      )}
    </div>
  );
}
