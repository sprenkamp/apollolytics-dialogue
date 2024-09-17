import requests
import logging
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory
from src.prompts.system_prompts import system_prompts
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)

class ApollolyticsDialogueAsync:
    def __init__(self, dialogue_type, model_name="gpt-4o", verbose=False):
        self.llm = ChatOpenAI(model_name=model_name)
        self.dialogue_type = dialogue_type
        self.verbose = verbose  # Make verbose configurable

    async def detect_propaganda(self, input_article):
        """
        Sends the input article to an external API for propaganda detection asynchronously.
        Returns the response or an error message in case of failure.
        """
        url = 'http://13.48.71.178:8000/analyze_propaganda'
        headers = {'Content-Type': 'application/json'}
        data = {
            "model_name": "gpt-4o",
            "contextualize": "true",
            "text": input_article
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logging.error("Propaganda detection service timed out.")
            return self.format_error("The propaganda detection service timed out. Please try again later.")
        except httpx.RequestError as e:
            logging.error(f"Error connecting to the propaganda detection service: {e}")
            return self.format_error("Failed to connect to the server. Please try again.")
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
