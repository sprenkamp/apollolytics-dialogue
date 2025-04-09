class Logger {
  constructor() {
    this.logs = [];
    this.maxLogs = 1000; // Maximum number of logs to keep
    this.loadLogs();
  }

  loadLogs() {
    try {
      const savedLogs = localStorage.getItem('frontendLogs');
      if (savedLogs) {
        this.logs = JSON.parse(savedLogs);
      }
    } catch (error) {
      console.error('Error loading logs:', error);
    }
  }

  saveLogs() {
    try {
      // Keep only the most recent logs
      if (this.logs.length > this.maxLogs) {
        this.logs = this.logs.slice(-this.maxLogs);
      }
      localStorage.setItem('frontendLogs', JSON.stringify(this.logs));
    } catch (error) {
      console.error('Error saving logs:', error);
    }
  }

  log(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      data
    };

    // Add to logs
    this.logs.push(logEntry);
    this.saveLogs();

    // Log to console with color coding
    const styles = {
      INFO: 'color: blue',
      ERROR: 'color: red',
      DEBUG: 'color: gray'
    };

    console.log(
      `%c[${timestamp}] [${level}] ${message}`,
      styles[level] || 'color: black'
    );
    if (data) {
      console.log(data);
    }
  }

  info(message, data = null) {
    this.log('INFO', message, data);
  }

  error(message, data = null) {
    this.log('ERROR', message, data);
  }

  debug(message, data = null) {
    this.log('DEBUG', message, data);
  }

  // Helper method to view logs in console
  showLogs() {
    console.log('=== Frontend Logs ===');
    this.logs.forEach(log => {
      console.log(`[${log.timestamp}] [${log.level}] ${log.message}`);
      if (log.data) console.log(log.data);
    });
  }

  // Clear all logs
  clearLogs() {
    this.logs = [];
    localStorage.removeItem('frontendLogs');
    console.log('Logs cleared');
  }
}

// Export a singleton instance
const logger = new Logger();
export default logger; 