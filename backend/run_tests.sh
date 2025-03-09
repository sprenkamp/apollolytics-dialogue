#!/bin/bash
# Run all Realtime API tests

# Set colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Apollolytics Realtime API Test Suite ===${NC}"
echo

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}OPENAI_API_KEY is not set. Please set it before running this script.${NC}"
    echo "Example: export OPENAI_API_KEY=your-api-key"
    exit 1
fi

# Generate test audio for audio tests
echo -e "${YELLOW}Generating test audio file...${NC}"
python generate_test_audio.py --duration 2.0 --frequency 440
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to generate test audio. Make sure you have NumPy installed.${NC}"
    echo "Try: pip install numpy"
    exit 1
fi
echo -e "${GREEN}Test audio generated successfully.${NC}"
echo

# Check if server is running (simple check - doesn't guarantee it's our server)
echo -e "${YELLOW}Checking if server is running on port 8000...${NC}"
nc -z localhost 8000
if [ $? -ne 0 ]; then
    echo -e "${RED}No server detected on port 8000. Please start the server first.${NC}"
    echo "Run in another terminal: uvicorn ws_speech_real-time:app --host 0.0.0.0 --port 8000"
    exit 1
fi
echo -e "${GREEN}Server appears to be running.${NC}"
echo

# Run basic test - critical mode
echo -e "${YELLOW}Running basic text-only test in critical mode...${NC}"
python test_realtime_api.py --mode critical 
if [ $? -ne 0 ]; then
    echo -e "${RED}Basic test (critical mode) failed.${NC}"
    exit 1
fi
echo -e "${GREEN}Basic test (critical mode) completed.${NC}"
echo

# Run basic test - supportive mode
echo -e "${YELLOW}Running basic text-only test in supportive mode...${NC}"
python test_realtime_api.py --mode supportive
if [ $? -ne 0 ]; then
    echo -e "${RED}Basic test (supportive mode) failed.${NC}"
    exit 1
fi
echo -e "${GREEN}Basic test (supportive mode) completed.${NC}"
echo

# Run audio test
echo -e "${YELLOW}Running test with audio input...${NC}"
python test_realtime_api.py --audio --test-audio-path test.wav
if [ $? -ne 0 ]; then
    echo -e "${RED}Audio test failed.${NC}"
    exit 1
fi
echo -e "${GREEN}Audio test completed.${NC}"
echo

# Run full conversation test - critical mode
echo -e "${YELLOW}Running full conversation test in critical mode...${NC}"
python test_full_conversation.py --mode critical --turns 2 --log critical_conversation.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Full conversation test (critical mode) failed.${NC}"
    exit 1
fi
echo -e "${GREEN}Full conversation test (critical mode) completed. See critical_conversation.txt for details.${NC}"
echo

# Run full conversation test - supportive mode
echo -e "${YELLOW}Running full conversation test in supportive mode...${NC}"
python test_full_conversation.py --mode supportive --turns 2 --log supportive_conversation.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Full conversation test (supportive mode) failed.${NC}"
    exit 1
fi
echo -e "${GREEN}Full conversation test (supportive mode) completed. See supportive_conversation.txt for details.${NC}"
echo

echo -e "${GREEN}=== All tests completed successfully! ===${NC}"