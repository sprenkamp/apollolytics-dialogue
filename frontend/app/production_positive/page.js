"use client";

import { useState, useRef, useEffect } from "react";
import RecordRTC, { StereoAudioRecorder } from "recordrtc";

export default function ConversationPage() {
  // Conversation state
  const [article, setArticle] = useState("");
  const [conversationStarted, setConversationStarted] = useState(false);
  const [assistantAudio, setAssistantAudio] = useState(null);

  // UI state for spinners and recording controls
  const [loadingMessage, setLoadingMessage] = useState(""); // "Analyzing article..." or "Thinking..."
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");
  const [audioFinished, setAudioFinished] = useState(false);

  // Refs for WebSocket, recorder, and media stream
  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);

  // Establish the conversation via WebSocket and send the initial "start" message.
  const startConversation = () => {
    if (!article.trim()) {
      alert("Article text is required to start the conversation.");
      return;
    }

    const ws = new WebSocket("ws://localhost:8000/ws/conversation");
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connection opened");
      setConversationStarted(true);
      setLoadingMessage("Analyzing article...");
      // Send the "start" message with the article text.
      ws.send(
        JSON.stringify({
          type: "start",
          article: article,
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const msgType = data.type;
      const payload = data.payload;

      if (msgType === "assistant_delta") {
        // Update audio if delta includes audio.
        if (payload.audio) {
          const audioSrc = payload.audio.startsWith("data:")
            ? payload.audio
            : `data:audio/wav;base64,${payload.audio}`;
          setAssistantAudio(audioSrc);
        }
      } else if (msgType === "assistant_final") {
        // Clear spinner and allow recording.
        setLoadingMessage("");
        setAudioFinished(true);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
      // Optionally add reconnection logic here.
    };
  };

  // Start recording using RecordRTC.
  const startRecording = async () => {
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

  // Stop recording, send audio over WebSocket, and show a "Thinking..." spinner.
  const stopRecording = () => {
    if (!recorderRef.current) return;

    recorderRef.current.stopRecording(() => {
      const wavBlob = recorderRef.current.getBlob();
      // Stop all tracks from the media stream.
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      setIsRecording(false);
      setRecordingStatus("");
      setLoadingMessage("Thinking...");

      // Convert the blob to base64.
      const reader = new FileReader();
      reader.onload = (e) => {
        const wavBase64 = btoa(e.target.result);
        const userMessage = {
          type: "user",
          content: [
            {
              type: "input_audio",
              input_audio: {
                data: wavBase64,
                format: "wav",
              },
            },
          ],
        };
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify(userMessage));
        } else {
          console.error("WebSocket is not open");
        }
      };
      reader.readAsBinaryString(wavBlob);
    });
  };

  // Clean up WebSocket connection when the component unmounts.
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="container">
      <h1 className="title">Apollolytics Dialogue</h1>

      {/* Step 1: Article input */}
      {!conversationStarted ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            startConversation();
          }}
          className="form"
        >
          <label htmlFor="article" className="form-label">
            Enter your propagandistic article text:
          </label>
          <textarea
            id="article"
            value={article}
            onChange={(e) => setArticle(e.target.value)}
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
          {/* Step 2: Display spinner when analyzing article or thinking */}
          {loadingMessage && (
            <div className="spinner-container">
              <div className="spinner"></div>
              <p>{loadingMessage}</p>
            </div>
          )}

          {/* Step 3: Assistant audio response */}
          {assistantAudio && (
            <audio
              controls
              autoPlay
              src={assistantAudio}
              className="audio-player"
              onEnded={() => {
                // Enable recording only after the assistant's audio finishes.
                setAudioFinished(true);
              }}
            />
          )}

          {/* Step 4: Recording control */}
          {audioFinished && !isRecording && (
            <button onClick={startRecording} className="button">
              Record Response
            </button>
          )}
          {isRecording && (
            <button onClick={stopRecording} className="button">
              Stop Recording
            </button>
          )}

          {/* Optionally, display recording status */}
          {recordingStatus && (
            <div className="recording-status">{recordingStatus}</div>
          )}
        </div>
      )}
    </div>
  );
}
