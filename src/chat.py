# chatbot.py
import requests
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory

from prompts.system_prompts import system_prompts

class ApollolyticsDialogue:
    def __init__(self, dialogue_type, model_name="gpt-4o"):
        self.llm = ChatOpenAI(model_name=model_name)
        self.dialogue_type = dialogue_type

    def detect_propaganda(self, input_article):
        url = 'http://13.48.71.178:8000/analyze_propaganda'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "model_name": "gpt-4o",
            "contextualize": "true",
            "text": input_article
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Request failed with status code {response.status_code}"}

    def create_conversation_chain(self, input_article, detected_propaganda):
        system_prompt = system_prompts[self.dialogue_type].content.format(
            input_article=input_article, result=detected_propaganda
        )
        # Create the conversation chain
        conversation = ConversationChain(
            llm=self.llm,
            verbose=True,
            memory=ConversationBufferMemory()
        )
        # Add the system message to the conversation
        conversation.memory.chat_memory.add_message(SystemMessage(content=system_prompt))
        return system_prompt, conversation

    def process_user_input(self, conversation_chain, user_input):
        response = conversation_chain.predict(input=user_input)
        return response