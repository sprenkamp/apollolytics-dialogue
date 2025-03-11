/**
 * Configuration utility for the application
 * Automatically selects between local and production endpoints
 */

const isDevelopment = () => {
  return process.env.NODE_ENV === 'development' || 
         (typeof window !== 'undefined' && window.location.hostname === 'localhost');
};

const getWebsocketUrl = () => {
  return isDevelopment() 
    ? 'ws://localhost:8080/ws/conversation'
    : 'wss://21b5-16-170-227-168.ngrok-free.app/ws/conversation';
};

const config = {
  isDevelopment,
  getWebsocketUrl,
};

export default config;