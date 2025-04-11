"use client";

import { useState, useRef, useEffect } from "react";
import logger from "../utils/logger";

export default function DialogueChatConfigurable({ websocketUrl, promptConfig }) {
  // Conversation state
  const [article, setArticle] = useState("");
  const [conversationStarted, setConversationStarted] = useState(false);
  const [assistantAudio, setAssistantAudio] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [audioQueue, setAudioQueue] = useState([]); // Queue for audio chunks
  const [isPlaying, setIsPlaying] = useState(false);

  // UI state for spinners and recording controls
  const [loadingMessage, setLoadingMessage] = useState(""); // "Analyzing article..." or "Thinking..."
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");
  const [audioFinished, setAudioFinished] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true); // Always show transcript panel
  const [audioStarted, setAudioStarted] = useState(false);
  const [pendingAssistantResponse, setPendingAssistantResponse] = useState(""); // Buffer for current assistant response until audio finishes

  // Refs for WebSocket, recorder, media stream, and audio context
  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const transcriptRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  // Audio recording state
  const [audioContext, setAudioContext] = useState(null);
  const [audioProcessor, setAudioProcessor] = useState(null);
  const [audioSource, setAudioSource] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);

  // Initialize audio context
  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Process audio queue
  useEffect(() => {
    const processAudioQueue = async () => {
      if (isPlayingRef.current || audioQueueRef.current.length === 0) {
        logger.debug('Audio queue processing skipped', {
          isPlaying: isPlayingRef.current,
          queueLength: audioQueueRef.current.length
        });
        return;
      }
      
      logger.info('Starting audio queue processing');
      isPlayingRef.current = true;
      setIsPlaying(true);
      
      // Use the existing AudioContext instead of creating a new one
      const audioContext = audioContextRef.current;
      let currentTime = audioContext.currentTime;
      
      try {
        while (audioQueueRef.current.length > 0) {
          // Skip processing if we're recording
          if (isRecording) {
            logger.debug('Skipping audio processing while recording');
            break;
          }

          const audioData = audioQueueRef.current.shift();
          logger.debug('Processing audio chunk', { size: audioData.length });
          
          // Convert base64 to ArrayBuffer
          const binaryString = atob(audioData);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          
          // Create WAV header
          const wavHeader = new Uint8Array(44);
          const view = new DataView(wavHeader.buffer);
          
          // RIFF header
          view.setUint32(0, 0x46464952, true); // "RIFF"
          view.setUint32(4, 36 + bytes.length, true); // file length
          view.setUint32(8, 0x45564157, true); // "WAVE"
          
          // fmt chunk
          view.setUint32(12, 0x20746D66, true); // "fmt "
          view.setUint32(16, 16, true); // length of format chunk
          view.setUint16(20, 1, true); // format type (1 = PCM)
          view.setUint16(22, 1, true); // number of channels
          view.setUint32(24, 24000, true); // sample rate
          view.setUint32(28, 24000 * 2, true); // byte rate
          view.setUint16(32, 2, true); // block align
          view.setUint16(34, 16, true); // bits per sample
          
          // data chunk
          view.setUint32(36, 0x61746164, true); // "data"
          view.setUint32(40, bytes.length, true); // data length
          
          // Combine header and audio data
          const wavData = new Uint8Array(wavHeader.length + bytes.length);
          wavData.set(wavHeader);
          wavData.set(bytes, wavHeader.length);
          
          // Decode audio data
          const audioBuffer = await audioContext.decodeAudioData(wavData.buffer);
          logger.debug('Audio decoded successfully', { duration: audioBuffer.duration });
          
          // Create and schedule the audio source
          const source = audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioContext.destination);
          
          // Schedule the audio to play at the current time
          source.start(currentTime);
          
          // Update the current time for the next chunk
          currentTime += audioBuffer.duration;
          
          // Clean up the source when it's done playing
          source.onended = () => {
            logger.debug('Audio chunk finished playing');
          };
        }
        
        // Wait for all audio to finish playing
        await new Promise(resolve => {
          const checkInterval = setInterval(() => {
            if (audioContext.currentTime >= currentTime) {
              clearInterval(checkInterval);
              resolve();
            }
          }, 100);
        });
        
      } catch (error) {
        logger.error('Error playing audio chunk', error);
      } finally {
        // Don't close the audio context here
        logger.info('Audio queue processing completed');
        isPlayingRef.current = false;
        setIsPlaying(false);
        setAudioFinished(true);
      }
    };

    processAudioQueue();
  }, [audioQueue, isRecording]);

  // Auto-scroll the transcript to bottom
  useEffect(() => {
    if (transcriptRef.current) {
      const scrollHeight = transcriptRef.current.scrollHeight;
      const clientHeight = transcriptRef.current.clientHeight;
      const maxScrollTop = scrollHeight - clientHeight;
      transcriptRef.current.scrollTop = maxScrollTop;
    }
  }, [transcript]);

  // Establish the conversation via WebSocket and send the initial "start" message.
  const startConversation = () => {
    if (!article.trim()) {
      alert("Article text is required to start the conversation.");
      return;
    }

    // Reset state for new conversation, but preserve transcript history
    setAssistantAudio(null);
    setAudioStarted(false);
    setAudioFinished(false);
    setPendingAssistantResponse("");
    setAudioQueue([]);
    audioQueueRef.current = [];
    
    const ws = new WebSocket(websocketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      logger.info("WebSocket connection opened");
      setConversationStarted(true);
      setLoadingMessage("Analyzing article...");
      // Send the "start" message with the article text and dialogue mode
      ws.send(
        JSON.stringify({
          type: "start",
          article: article,
          mode: promptConfig.mode
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const msgType = data.type;
      const payload = data.payload;

      logger.debug("WebSocket message received", {
        type: msgType,
        payload: payload ? {
          ...payload,
          audio: payload.audio ? `[Audio data length: ${payload.audio.length}]` : undefined
        } : undefined
      });

      if (msgType === "assistant_delta") {
        if (payload.text) {
          logger.debug("Assistant delta text received", { text: payload.text });
          setAudioStarted(true);
          // Only update pending response if it's empty or if this is a new message
          if (!pendingAssistantResponse) {
            setPendingAssistantResponse(payload.text);
          } else {
            setPendingAssistantResponse(prev => prev + payload.text);
          }
        }
        
        if (payload.audio) {
          logger.debug("Received audio chunk", { length: payload.audio.length });
          const audioData = payload.audio.startsWith("data:") 
            ? payload.audio.split(",")[1] 
            : payload.audio;
          
          logger.debug("Processed audio data", { length: audioData.length });
          
          setAudioQueue(prev => {
            const newQueue = [...prev, audioData];
            logger.debug("Updated audio queue", { length: newQueue.length });
            return newQueue;
          });
          audioQueueRef.current.push(audioData);
          logger.debug("Audio queue ref updated", { length: audioQueueRef.current.length });
        }
      } else if (msgType === "assistant_final") {
        logger.info("Assistant final message received");
        setLoadingMessage("");
        
        if (!isPlaying) {
          logger.debug("Audio finished, enabling recording");
          setAudioFinished(true);
        }
        
        if (payload.text) {
          logger.debug("Assistant final text received", { text: payload.text });
          setPendingAssistantResponse(payload.text);
          
          // Add assistant message to transcript when audio finishes
          if (!isPlaying) {
            setTranscript(prev => [
              ...prev,
              {
                id: `assistant_${Date.now()}`,
                role: "assistant",
                content: payload.text,
                final: true
              }
            ]);
            // Clear pending response after adding to transcript
            setPendingAssistantResponse("");
          }
        }
      } else if (msgType === "user_transcript") {
        if (payload.text || payload.transcript) {
          logger.debug("User transcript received", { text: payload.text || payload.transcript });
          
          setTranscript(prev => {
            // Remove any placeholder messages
            const withoutPlaceholder = prev.filter(msg => !msg.isPlaceholder);
            
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
        if (payload.transcript) {
          logger.debug("Received automatic transcription", { transcript: payload.transcript });
          
          setTranscript(prev => {
            // Remove any placeholder messages
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
      }
    };

    ws.onerror = (err) => {
      logger.error("WebSocket error", err);
    };

    ws.onclose = () => {
      logger.info("WebSocket connection closed");
    };
  };

  // Start recording
  const startRecording = async () => {
    try {
      // Stop any playing audio by clearing the queue
      setAudioQueue([]);
      audioQueueRef.current = [];
      setIsPlaying(false);
      isPlayingRef.current = false;
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream; // Store stream reference
      
      const context = new AudioContext({
        sampleRate: 24000, // Match OpenAI's required sample rate
        channelCount: 1,   // Mono audio
      });
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      
      // Store all audio data
      const chunks = [];
      
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        
        // Convert float32 to int16
        for (let i = 0; i < inputData.length; i++) {
          pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
        }
        
        chunks.push(pcmData);
      };

      source.connect(processor);
      processor.connect(context.destination);
      
      // Store references for cleanup
      setAudioContext(context);
      setAudioProcessor(processor);
      setAudioSource(source);
      setAudioChunks(chunks);
      
      setIsRecording(true);
      setRecordingStatus("Recording...");
      logger.info("Started recording audio");
    } catch (error) {
      console.error('Error starting recording:', error);
      logger.error("Failed to start recording", error);
    }
  };

  // Stop recording and clean up
  const stopRecording = () => {
    if (audioProcessor && audioSource && streamRef.current) {
      // Stop all tracks from the media stream
      streamRef.current.getTracks().forEach(track => track.stop());
      
      audioSource.disconnect();
      audioProcessor.disconnect();
      audioContext.close();
      
      // Combine all audio chunks
      const totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const combinedPcm = new Int16Array(totalLength);
      let offset = 0;
      
      audioChunks.forEach(chunk => {
        combinedPcm.set(chunk, offset);
        offset += chunk.length;
      });
      
      // Convert to base64 more efficiently
      const uint8Array = new Uint8Array(combinedPcm.buffer);
      let binary = '';
      for (let i = 0; i < uint8Array.length; i++) {
        binary += String.fromCharCode(uint8Array[i]);
      }
      const base64Audio = btoa(binary);
      
      // Send the complete audio
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "user",
          content: [{
            type: "input_audio",
            input_audio: {
              data: base64Audio
            }
          }]
        }));
        logger.info("Sent complete audio recording", { size: base64Audio.length });
      }
      
      // Reset state
      setIsRecording(false);
      setRecordingStatus("");
      setAudioChunks([]);
      setAudioContext(null);
      setAudioProcessor(null);
      setAudioSource(null);
      streamRef.current = null;
      
      logger.info("Stopped recording audio");
    }
  };

  // Toggle recording
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
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
      <h1 className="title">{promptConfig.title}</h1>
      
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
            {promptConfig.articlePrompt}
          </label>
          <div className="article-input-container">
            <textarea
              id="article"
              value={article}
              onChange={(e) => setArticle(e.target.value)}
              className="textarea"
              rows={8}
              required
            />
          </div>
          <button type="submit" className="button">
            Start Conversation
          </button>
        </form>
      ) : (
        <div className="conversation-container">
          <div className="conversation">
            {/* Step 2: Display spinner when analyzing article or thinking */}
            {loadingMessage && (
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
                }}
              />
            )}

            {/* Step 4: Recording control */}
            {audioFinished && (
              <button 
                onClick={toggleRecording} 
                className={`button ${isRecording ? 'recording-button' : ''}`}
              >
                {isRecording ? "Stop Recording" : "Record Response"}
              </button>
            )}

            {/* Optionally, display recording status */}
            {recordingStatus && (
              <div className="recording-status">{recordingStatus}</div>
            )}
            
            {/* Show transcript toggle button */}
            <button 
              onClick={() => setShowTranscript(prev => !prev)} 
              className="transcript-toggle-button"
            >
              {showTranscript ? "Hide Transcript" : "Show Transcript"}
            </button>
          </div>
          
          {/* Transcript panel */}
          {showTranscript && (
            <div className="transcript-panel" ref={transcriptRef}>
              <h2>Conversation Transcript</h2>
              <div className="transcript-messages">
                {transcript.map((message) => (
                  <div 
                    key={message.id} 
                    className={`message ${message.role}`}
                  >
                    <div className="message-header">
                      <span className="message-role">{message.role === 'assistant' ? 'Assistant' : 'You'}</span>
                      <span className="message-time">{new Date().toLocaleTimeString()}</span>
                    </div>
                    <div className="message-content">{message.content}</div>
                  </div>
                ))}
                {pendingAssistantResponse && !isPlaying && (
                  <div className="message assistant">
                    <div className="message-header">
                      <span className="message-role">Assistant</span>
                      <span className="message-time">{new Date().toLocaleTimeString()}</span>
                    </div>
                    <div className="message-content">{pendingAssistantResponse}</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}