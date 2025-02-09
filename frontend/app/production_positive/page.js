"use client";

import axios from "axios";
import { useState, useRef } from "react";
import RecordRTC, { StereoAudioRecorder } from "recordrtc";

const API_BASE = "http://localhost:8000";

async function startConversationRequest(article) {
  const payload = { article };
  const res = await axios.post(`${API_BASE}/conversation/start`, payload, {
    withCredentials: true,
  });
  return res.data;
}

async function sendAudioResponse(base64Audio) {
  const payload = { message: base64Audio };
  const res = await axios.post(`${API_BASE}/conversation/respond`, payload, {
    withCredentials: true,
  });
  return res.data;
}

export default function ConversationPage() {
  const [article, setArticle] = useState("");
  const [conversationStarted, setConversationStarted] = useState(false);

  // Assistant audio and audio player states
  const [assistantAudio, setAssistantAudio] = useState(null);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioFinished, setAudioFinished] = useState(false);

  // Recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");

  // Loading / spinner message
  const [loadingMessage, setLoadingMessage] = useState("");

  // References to recorder and stream
  const recorderRef = useRef(null);
  const streamRef = useRef(null);

  const handleStartConversation = async (e) => {
    e.preventDefault();
    if (!article.trim()) {
      alert("Article text is required to start the conversation.");
      return;
    }

    setConversationStarted(true);
    setAudioPlaying(true);

    // Clear any old audio and set spinner message
    setAssistantAudio(null);
    setLoadingMessage("Analyzing article...");

    try {
      const data = await startConversationRequest(article);

      // Construct a proper data URI for the received audio
      const audioSrc = data.audio.startsWith("data:")
        ? data.audio
        : `data:audio/wav;base64,${data.audio}`;

      setAssistantAudio(audioSrc);
      setLoadingMessage(""); // Clear the spinner message once audio is ready
    } catch (err) {
      console.error(err);
      alert("Error starting conversation.");
      setLoadingMessage("");
    }
  };

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new RecordRTC(stream, {
        type: "audio",
        mimeType: "audio/wav",
        recorderType: StereoAudioRecorder,
      });
      recorderRef.current = recorder;
      recorder.startRecording();
      setIsRecording(true);
      setRecordingStatus("Recording...");
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Could not access your microphone.");
    }
  };

  const handleStopRecording = () => {
    if (!recorderRef.current) return;

    recorderRef.current.stopRecording(async () => {
      const wavBlob = recorderRef.current.getBlob();
      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      setIsRecording(false);
      setRecordingStatus("");

      // Prepare "Thinking..." spinner while we wait for the response
      setAssistantAudio(null);
      setLoadingMessage("Thinking...");

      // Convert blob to base64 and send to server
      const reader = new FileReader();
      reader.onload = async (e) => {
        const wavBase64 = btoa(e.target.result);
        setAudioPlaying(true);

        try {
          const data = await sendAudioResponse(wavBase64);

          const audioSrc = data.audio.startsWith("data:")
            ? data.audio
            : `data:audio/wav;base64,${data.audio}`;

          setAssistantAudio(audioSrc);
          setLoadingMessage("");
          setAudioFinished(false);
        } catch (err) {
          console.error(err);
          alert("Error continuing conversation.");
          setLoadingMessage("");
        }
      };
      reader.readAsBinaryString(wavBlob);
    });
  };

  return (
    <div className="container">
      <h1 className="title">Apollolytics Dialogue</h1>

      {!conversationStarted ? (
        <form onSubmit={handleStartConversation} className="form">
          <label htmlFor="article" className="form-label">
            Enter your article text:
          </label>
          <textarea
            id="article"
            value={article}
            onChange={(e) => setArticle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleStartConversation(e);
              }
            }}
            className="textarea"
            rows={4}
            required
          />
          <button type="submit" className="button">
            Start Conversation
          </button>
        </form>
      ) : (
        <div className="conversation">
          {/* If we have a loading message and no audio, show spinner */}
          {loadingMessage && !assistantAudio && (
            <div className="spinner-container">
              <div className="spinner"></div>
              <p>{loadingMessage}</p>
            </div>
          )}

          {/* If audio is available, render it */}
          {assistantAudio && (
            <>
              <audio
                controls
                autoPlay
                src={assistantAudio}
                className="audio-player"
                onPlay={() => setAudioPlaying(true)}
                onEnded={() => {
                  setAudioPlaying(false);
                  setAudioFinished(true);
                }}
              />
              {/* Show record button only after audio finishes */}
              {audioFinished && (
                <button
                  onClick={isRecording ? handleStopRecording : handleStartRecording}
                  className="button"
                >
                  {isRecording ? "Stop Recording" : "Record Response"}
                </button>
              )}
            </>
          )}

          {/* Recording status indicator */}
          {recordingStatus && (
            <span className="recording-status">{recordingStatus}</span>
          )}
        </div>
      )}
    </div>
  );
}
