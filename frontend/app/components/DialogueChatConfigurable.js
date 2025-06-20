"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from 'next/dynamic';

// Dynamically import confetti to avoid SSR issues
const ReactConfetti = dynamic(() => import('react-confetti'), {
  ssr: false
});

export default function DialogueChatConfigurable({ websocketUrl, promptConfig, initialArticle, prolificId }) {
  // Conversation state
  const [article, setArticle] = useState(initialArticle || "");
  const [conversationStarted, setConversationStarted] = useState(false);
  const [assistantAudio, setAssistantAudio] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [conversationEnded, setConversationEnded] = useState(false);
  const [endMessage, setEndMessage] = useState("");
  const [showConfetti, setShowConfetti] = useState(false);
  const [showEndTranscript, setShowEndTranscript] = useState(false);
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0
  });

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // UI state for spinners and recording controls
  const [loadingMessage, setLoadingMessage] = useState(""); // "Analyzing article..." or "Thinking..."
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");
  const [audioFinished, setAudioFinished] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true); // Always show transcript panel
  const [audioStarted, setAudioStarted] = useState(false);
  const [pendingAssistantResponse, setPendingAssistantResponse] = useState(""); // Buffer for current assistant response until audio finishes

  // Timing state
  const [assistantResponseTime, setAssistantResponseTime] = useState(null);
  const [recordingStartTime, setRecordingStartTime] = useState(null);

  // Refs for WebSocket, recorder, and media stream
  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const transcriptRef = useRef(null);

  // Auto-scroll the transcript to bottom
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcript]);

  // Establish the conversation via WebSocket and send the initial "start" message.
  const startConversation = () => {
    if (!article.trim()) {
      alert("Article text is required to start the conversation.");
      return;
    }

    // Reset state for new conversation
    setAssistantAudio(null);
    setAudioStarted(false);
    setAudioFinished(false);
    setPendingAssistantResponse("");
    
    const ws = new WebSocket(websocketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connection opened");
      setConversationStarted(true);
      setLoadingMessage("Analyzing article...");
      
      // Get the current origin and full URL for logging/analytics
      const origin_url = typeof window !== 'undefined' ? window.location.href : null;
      
      // Send the "start" message with the article text, dialogue mode, and origin URL
      ws.send(
        JSON.stringify({
          type: "start",
          article: article,
          mode: promptConfig.mode,
          origin_url: origin_url,
          prolific_id: prolificId
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const msgType = data.type;
      const payload = data.payload;

      console.log("WebSocket message received:", msgType, payload);

      if (msgType === "assistant_delta") {
        // Handle text and audio in parallel - audio can come in first message or later
        
        // Store text in the pending response until audio finishes
        if (payload.text) {
          console.log("Assistant delta:", payload.text);
          
          // Once we get text, we can enable audio to start playing
          setAudioStarted(true);
          
          // Accumulate the assistant's response to reveal after audio finishes
          setPendingAssistantResponse(prev => prev + payload.text);
        }
        
        // Update audio if delta includes audio and we're ready to play it
        if (payload.audio) {
          const audioSrc = payload.audio.startsWith("data:")
            ? payload.audio
            : `data:audio/wav;base64,${payload.audio}`;
          setAssistantAudio(audioSrc);
        }
      } else if (msgType === "assistant_final") {
        // Clear spinner but only allow recording if audio is finished
        setLoadingMessage("");
        
        // If there's no audio component, or audio has already finished, enable recording
        if (!assistantAudio) {
          setAudioFinished(true);
        }
        
        // Final assistant message received - store the complete text
        if (payload.text) {
          console.log("Assistant final:", payload.text);
          // Replace pending response with final text if provided
          setPendingAssistantResponse(payload.text);
        }
      } else if (msgType === "user_transcript") {
        // This follows the OpenAI API conversation.item.input_audio_transcription.completed pattern
        if (payload.text || payload.transcript) {
          // Debug log
          console.log("User transcript received:", payload.text || payload.transcript);
          
          // Remove any processing placeholder and add the actual transcript
          setTranscript(prev => {
            // First remove any non-final user messages
            const withoutPlaceholder = prev.filter(msg => !msg.isPlaceholder);
            
            // Then add the new transcript
            return [
              ...withoutPlaceholder,
              { 
                id: payload.item_id || `user_${Date.now()}`, 
                role: "user", 
                content: payload.transcript || payload.text, 
                final: true 
              }
            ];
          });
        }
      } else if (msgType === "conversation.item.input_audio_transcription.completed") {
        // Handle the automatic transcription event from the OpenAI Realtime API
        if (payload.transcript) {
          console.log("Received automatic transcription:", payload.transcript);
          
          // Update transcript with the transcribed text
          setTranscript(prev => {
            // Remove any placeholder user messages
            const withoutPlaceholder = prev.filter(msg => !msg.isPlaceholder);
            
            return [
              ...withoutPlaceholder,
              {
                id: payload.item_id || `user_${Date.now()}`,
                role: "user",
                content: payload.transcript,
                final: true
              }
            ];
          });
        }
      } else if (msgType === "conversation_end") {
        console.log("Processing conversation end message:", payload);
        // Clear all UI states
        setConversationEnded(true);
        setEndMessage(payload.message);
        setLoadingMessage("");
        setAudioFinished(false);
        setAssistantAudio(null);
        setIsRecording(false);
        setRecordingStatus("");
        setAudioStarted(false);
        setPendingAssistantResponse("");
        // Show confetti
        setShowConfetti(true);
        // Hide confetti after 5 seconds
        setTimeout(() => setShowConfetti(false), 5000);
        // Close the WebSocket connection
        if (wsRef.current) {
          console.log("Closing WebSocket connection");
          wsRef.current.close();
        }
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
    };
  };

  // Start recording using dynamic import of RecordRTC.
  const startRecording = async () => {
    try {
      // Dynamically import RecordRTC and its StereoAudioRecorder.
      const { default: RecordRTC, StereoAudioRecorder } = await import("recordrtc");

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
      setRecordingStartTime(Date.now());
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
      
      // Reset audio state for next response
      setAssistantAudio(null);
      setAudioStarted(false);
      setAudioFinished(false);
      setPendingAssistantResponse("");

      // Following the OpenAI API pattern, we'll add a temporary placeholder
      // and wait for the conversation.item.input_audio_transcription.completed event
      setTranscript(prev => [
        ...prev,
        { 
          id: `placeholder_${Date.now()}`,
          role: "user", 
          content: "Processing your audio...", 
          final: false,
          isPlaceholder: true
        }
      ]);

      // Calculate timing metrics
      const thinkingTime = (recordingStartTime - assistantResponseTime) / 1000; // Time from assistant response to starting recording
      const recordingDuration = (Date.now() - recordingStartTime) / 1000; // Duration of recording
      const totalResponseTime = (Date.now() - assistantResponseTime) / 1000; // Total time from assistant response to end of recording

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
          timing: {
            thinking_time: thinkingTime,
            recording_duration: recordingDuration,
            total_response_time: totalResponseTime
          }
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
      {showConfetti && (
        <ReactConfetti
          width={windowSize.width}
          height={windowSize.height}
          recycle={false}
          numberOfPieces={200}
          gravity={0.3}
        />
      )}
      {/* Step 1: Article input */}
      {!conversationStarted ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            startConversation();
          }}
          className="form"
        >
          <div className="article-input-container">
            <textarea
              id="article"
              value={article}
              onChange={(e) => setArticle(e.target.value)}
              className="textarea"
              rows={8}
              required
              readOnly={!!initialArticle}
            />
          </div>
          <button type="submit" className="button">
            Start Conversation
          </button>
        </form>
      ) : (
        <div className="conversation-container">
          {conversationEnded ? (
            <div className="conversation-end">
              <div className="end-message">{endMessage}</div>
              <button 
                onClick={() => setShowEndTranscript(prev => !prev)} 
                className="transcript-toggle-button"
              >
                {showEndTranscript ? "Hide Transcript" : "Show Transcript"}
              </button>
              {showEndTranscript && (
                <div className="transcript-panel" ref={transcriptRef}>
                  <h2 className="transcript-title">Conversation Transcript</h2>
                  {transcript.length > 0 ? (
                    <div className="transcript-messages">
                      {transcript.map((message, index) => (
                        <div 
                          key={index} 
                          className={`transcript-message ${message.role === "assistant" ? "assistant" : "user"} ${!message.final ? "pending" : ""}`}
                        >
                          <div className="message-role">{message.role === "assistant" ? "Assistant" : "You"}</div>
                          <div className="message-content">{message.content}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-transcript">The conversation transcript will appear here.</p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="conversation">
              {/* Step 2: Display spinner when analyzing article or thinking */}
              {loadingMessage && !conversationEnded && (
                <div className="spinner-container">
                  <div className="spinner"></div>
                  <p>{loadingMessage}</p>
                </div>
              )}

              {/* Step 3: Assistant audio response */}
              {assistantAudio && audioStarted && (
                <audio
                  controls
                  autoPlay
                  src={assistantAudio}
                  className="audio-player"
                  onEnded={() => {
                    // Enable recording when audio finishes
                    setAudioFinished(true);
                    
                    // Add the assistant response to the transcript
                    if (pendingAssistantResponse) {
                      setTranscript(prev => [
                        ...prev,
                        {
                          id: `assistant_${Date.now()}`,
                          role: "assistant",
                          content: pendingAssistantResponse,
                          final: true
                        }
                      ]);
                    }
                    
                    // Update the assistant response time when audio finishes
                    setAssistantResponseTime(Date.now());
                  }}
                />
              )}

              {/* Step 4: Recording control */}
              {audioFinished && !isRecording && !conversationEnded && (
                <button onClick={startRecording} className="button">
                  Record Response
                </button>
              )}
              {isRecording && !conversationEnded && (
                <button onClick={stopRecording} className="button recording-button">
                  Stop Recording
                </button>
              )}

              {/* Optionally, display recording status */}
              {recordingStatus && !conversationEnded && (
                <div className="recording-status">{recordingStatus}</div>
              )}
              
              {/* Toggle transcript visibility */}
              {!conversationEnded && (
                <button 
                  onClick={() => setShowTranscript(prev => !prev)} 
                  className="transcript-toggle-button"
                >
                  {showTranscript ? "Hide Transcript" : "Show Transcript"}
                </button>
              )}
            </div>
          )}
          
          {/* Transcript panel - only show when not ended */}
          {showTranscript && !conversationEnded && (
            <div className="transcript-panel" ref={transcriptRef}>
              <h2 className="transcript-title">Conversation Transcript</h2>
              {transcript.length > 0 ? (
                <div className="transcript-messages">
                  {transcript.map((message, index) => (
                    <div 
                      key={index} 
                      className={`transcript-message ${message.role === "assistant" ? "assistant" : "user"} ${!message.final ? "pending" : ""}`}
                    >
                      <div className="message-role">{message.role === "assistant" ? "Assistant" : "You"}</div>
                      <div className="message-content">{message.content}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-transcript">The conversation transcript will appear here.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}