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
  const predefinedArticle = `
  NATO is no longer hiding that it is gearing up for a potential military conflict with Russia, Deputy Foreign Minister Aleksandr Grushko has said, pointing to this year's Steadfast Defender drills, the bloc's largest maneuvers since the end of the Cold War. 
  The US-led military bloc has been expanding eastward for decades, despite assurances given to the Soviet Union in the run-up to German reunification in 1990 that it would not do so. Russia has repeatedly described the expansion toward its borders as a threat to its security.
  
  Speaking to RIA Novosti on Tuesday, Grushko said that “now NATO representatives have stopped hiding that they are preparing for a potential armed clash with Russia.” 
  “Regional defense plans have been approved, concrete tasks for all of the bloc’s military command structures have been formulated. Possible options for military action against Russia are being continuously worked out,” the diplomat added. 
  
  He cited the Steadfast Defender exercise that ran from January through late May, saying that “for the first time, the enemy was not a fictitious state, but Russia.” 
  While NATO did not specifically name Russia in its announcement of the drills, it called the exercises preparation for a conflict with a “near-peer” adversary. 
  NATO’s main security document identifies Russia as the bloc’s largest threat. The drills, which were conducted near Russia’s western border, featured some 90,000 troops from all 32 NATO member states. 
  
  According to Grushko, “military budgets are being pumped [with money] and [Western] economies are being militarized.” The deputy foreign minister insisted that “it was not Russia, but the North-Atlantic alliance that took the path of confrontation,” by refusing to engage in dialogue with Moscow. 
  He concluded that NATO bears responsibility for a “major European security crisis.”
  
  On Saturday, Germany’s Die Welt newspaper, citing a confidential NATO planning document, reported that in preparation for a potential conflict with Russia, the military bloc is planning to dramatically increase the number of combat and air defense units. 
  Over the past few months, several NATO member states have claimed that Russia could be harboring plans to attack the bloc.
  
  Speaking on the sidelines of the St. Petersburg International Economic Forum (SPIEF) in June, Russian President Vladimir Putin dismissed as “nonsense” and “bulls**t” allegations that Moscow plans to attack NATO. 
  In September, the Russian leader warned, however, that should Ukraine’s Western backers allow Kiev to use their missiles to hit targets deep inside Russia, “it will mean nothing less than the direct participation of NATO countries, the US and European countries, in the conflict in Ukraine.”
  `;
  
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
