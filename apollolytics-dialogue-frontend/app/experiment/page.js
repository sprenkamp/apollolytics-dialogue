// app/experiment/page.js
"use client";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import styles from "../Home.module.css"; // Ensure this path is correct
import Link from "next/link"; // Import Link for navigation

export default function Experiment() {
  const [conversation, setConversation] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [articleSubmitted, setArticleSubmitted] = useState(false);
  const chatWindowRef = useRef(null); // Ref for auto-scrolling
  const backendUrl = "https://duly-fresh-alien.ngrok-free.app"; // Use environment variable or fallback

  // Predefined article (constant)
  const predefinedArticle = `Many of the billionaires who are backing US Vice President Kamala Harris in the upcoming election in November are likely “terrified” about Jeffrey Epstein’s client list becoming public in case of a Donald Trump victory, according to SpaceX and Tesla CEO Elon Musk.

Epstein worked as a financier and socialized with the rich and famous for decades. In 2019, he was arrested for pimping out young women, including many minors, to his powerful acquaintances, whom he often flew out to his private island in the Caribbean. The list of Epstein’s “guests” and other evidence, which has reportedly been gathered by the FBI, has since remained under lock and key, even after Epstein died under suspicious circumstances in his Manhattan cell in 2019, which has officially been ruled a suicide.

Last month, Donald Trump suggested in an interview with Lex Friedman that Epstein’s “black book” could be made public if he wins in November.

Speaking with former Fox News host Tucker Carlson on Monday, Musk claimed that the Democratic party’s presidential candidate Kamala Harris was simply a “marionette” and that there are actually over a hundred “puppet masters” behind her, most of whom the billionaire said he probably knows personally.

The tech mogul then went on to say that he would find it interesting to see a matchup of the top one hundred of these so-called “puppet masters” and the Jeffrey Epstein client list, suggesting there would be a “strong overlap” of the two.

While he did not comment on the likelihood of the list actually ever seeing the light of day, Musk suggested that a big part of why Kamala Harris has been getting so much support was because “many billionaires are terrified” that it could be made public if Trump wins.

He suggested that people like LinkedIn co-founder and Musk’s former VP of Development at PayPal Reid Hoffman and Microsoft’s Bill Gates were particularly concerned over the “Epstein situation” and that the Department of Justice could actually “move forward” on some of the evidence.

He also pointed out how “mind blowing” it was that after all these years, the US Justice system has not tried to prosecute even a single person from Epstein’s client list and has instead been going after protesters who took part in the January 6 Capitol Hill riots.`;

  // Handles predefined article submission
  const handleArticleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    try {
      const response = await axios.post(
        `${backendUrl}/analyze_propaganda_fake`, // Corrected template literal
        {
          article_text: predefinedArticle,
        },
        {
          withCredentials: true, // Ensures cookies are sent
        }
      );

      if (response.status === 200) {
        const result = response.data;
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
        `${backendUrl}/continue_conversation`, // Corrected template literal
        {
          user_input: userMessage,
        },
        {
          withCredentials: true, // Ensures cookies are sent
        }
      );

      if (response.status === 200) {
        const botResponse = response.data.bot_message;
        setConversation((prev) => [
          ...prev,
          { sender: "user", message: userMessage }, // User's message
          { sender: "bot", message: botResponse }, // Bot's response
        ]);
        setUserMessage(""); // Clear user input
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
      <h1 className={styles.header}>Apollolytics Dialogue - Experiment</h1>
      <Link href="/" className={styles.homeLink}>
        ← Back to Home
      </Link>

      {/* Predefined Article Submission */}
      {!articleSubmitted && (
        <form onSubmit={handleArticleSubmit} className={styles.inputForm}>
          <textarea
            value={predefinedArticle}
            readOnly
            className={styles.inputField}
            rows={10}
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
            disabled={loading}
          />
          <button type="submit" className={styles.sendButton} disabled={loading}>
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      )}
    </div>
  );
}
