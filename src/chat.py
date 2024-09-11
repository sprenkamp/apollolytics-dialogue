import requests
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory
from prompts.system_prompts import system_prompts

class ApollolyticsDialogue:
    def __init__(self, dialogue_type, model_name="gpt-4o", verbose=False):
        self.llm = ChatOpenAI(model_name=model_name)
        self.dialogue_type = dialogue_type
        self.verbose = verbose  # Make verbose configurable

    def detect_propaganda(self, input_article):
        """
        Sends the input article to an external API for propaganda detection.
        Returns the response or an error message in case of failure.
        """
        url = 'http://13.48.71.178:8000/analyze_propaganda'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "model_name": "gpt-4o",
            "contextualize": "true",
            "text": input_article
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Request failed with status code {response.status_code}"}
        except requests.exceptions.RequestException as e:
            # Fallback in case of network errors
            return {"error": f"Failed to connect to the server: {str(e)}"}

    def create_conversation_chain(self, input_article, detected_propaganda):
        """
        Creates a conversation chain initialized with a system prompt 
        and an initial Socratic response from the LLM.
        """
        # Ensure dialogue_type exists in system_prompts
        if self.dialogue_type not in system_prompts:
            return {"error": "Invalid dialogue type"}

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

        # Generate a Socratic question as the initial response
        initial_response = conversation.predict(input="What are your thoughts on the key points presented in the article? Do you recognize instances of propaganda or disinformation?")

        # Return the system prompt, conversation chain, and initial LLM response
        return system_prompt, conversation, initial_response

    def process_user_input(self, conversation_chain, user_input):
        """
        Processes the user input and generates a response using the conversation chain.
        """
        try:
            response = conversation_chain.predict(input=user_input)
            return response
        except Exception as e:
            return {"error": str(e)}

# Optional: If you wish to use asynchronous requests, use this method instead
# (Make sure you're running in an async environment)
import httpx

class ApollolyticsDialogueAsync(ApollolyticsDialogue):
    async def detect_propaganda(self, input_article):
        """
        Sends the input article to an external API for propaganda detection asynchronously.
        Returns the response or an error message in case of failure.
        """
        url = 'http://13.48.71.178:8000/analyze_propaganda'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "model_name": "gpt-4o",
            "contextualize": "true",
            "text": input_article
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Request failed with status code {response.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"Failed to connect to the server: {str(e)}"}
