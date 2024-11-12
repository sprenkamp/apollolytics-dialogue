import logging
import websockets
import asyncio
import json
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory
from src.prompts.system_prompts import system_prompts

# Configure logging
logging.basicConfig(level=logging.INFO)

class ApollolyticsDialogueAsync:
    def __init__(self, dialogue_type, model_name="gpt-4o-mini", verbose=False):
        self.llm = ChatOpenAI(model_name=model_name)
        self.dialogue_type = dialogue_type
        self.verbose = verbose  # Make verbose configurable
        self.websocket_url = 'ws://13.48.71.178:8000/ws/analyze_propaganda'  # WebSocket URL

    async def detect_propaganda(self, input_article):
        """
        Sends the input article to the WebSocket server for propaganda detection asynchronously.
        Waits for the entire response to be streamed and accumulates the data before returning.
        """
        data = {
            "model_name": "gpt-4o-mini",
            "contextualize": False,
            "text": input_article
        }

        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Send the input article as JSON
                await websocket.send(json.dumps(data))
                
                # Accumulate streamed responses
                full_response = ""
                
                while True:
                    try:
                        message = await websocket.recv()  # Receive streamed message
                        full_response += message  # Append to full response

                    except websockets.exceptions.ConnectionClosedOK:
                        # Exit when the server closes the connection cleanly
                        logging.info("WebSocket connection closed normally.")
                        break
                print(full_response)
                return json.loads(full_response)  # Return the accumulated full response

        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"Connection closed unexpectedly: {e}")
            return self.format_error("The connection to the propaganda detection service was closed unexpectedly.")
        except asyncio.TimeoutError:
            logging.error("Propaganda detection service timed out.")
            return self.format_error("The propaganda detection service timed out. Please try again later.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return self.format_error("An unexpected error occurred. Please try again.")

    async def create_conversation_chain(self, input_article, detected_propaganda):
        """
        Asynchronously creates a conversation chain initialized with a system prompt 
        and an initial Socratic response from the LLM.
        """
        # Ensure dialogue_type exists in system_prompts
        if self.dialogue_type not in system_prompts:
            return self.format_error("Invalid dialogue type")

        # Create the system prompt using the dialogue type, article, and detected propaganda
        system_prompt = system_prompts[self.dialogue_type].content.format(
            input_article=input_article, result=detected_propaganda
        )

        # Create the conversation chain with memory
        conversation = ConversationChain(
            llm=self.llm,
            verbose=self.verbose,  # Use the configurable verbose setting
            memory=ConversationBufferMemory()
        )

        # Add the system message to the conversation memory
        conversation.memory.chat_memory.add_message(SystemMessage(content=system_prompt))

        # Generate a Socratic question as the initial response asynchronously
        initial_response = await conversation.apredict(
            input="What are your thoughts on the key points presented in the article? Do you recognize instances of propaganda or disinformation?"
        )
        print(system_prompt)
        # Return the system prompt, conversation chain, and initial LLM response
        return system_prompt, conversation, initial_response

    async def process_user_input(self, conversation_chain, user_input):
        """
        Asynchronously processes the user input and generates a response using the conversation chain.
        """
        try:
            # Generate response asynchronously
            response = await conversation_chain.apredict(input=user_input)
            return response
        except Exception as e:
            logging.error(f"Error processing user input: {e}")
            return self.format_error(f"An error occurred while processing your input: {str(e)}")

    @staticmethod
    def format_error(message):
        """
        Standardize error responses.
        """
        return {"error": message}
