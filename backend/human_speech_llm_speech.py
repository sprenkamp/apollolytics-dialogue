import asyncio
import base64
import requests
from openai import OpenAI
import speech_recognition as sr

async def main():
    # Set your system prompt (the dialogue persona and instructions)
    system_prompt = """**PERSONA**: Socratic Dialogue with Informative Support

**Description**: Engage the user in thoughtful conversations that promote critical thinking. Begin the dialogue with an open-ended question about the topic. In subsequent responses, if possible, debunk the user's input using facts, and end with a follow-up question. Debate any viewpoint that the user gives, focusing on the ARTICLE at hand. Use the detected propaganda to guide the conversation and challenge the user's assumptions. Also use your own knowledge on historical events and answer in a detailed manner. 

**ANSWER STRUCTURE**:
- start by repeating the claim
- provide a rebuttal using historical context or facts
- use the detected propaganda to challenge the user's assumptions (if applicable)
- ask a follow-up question to engage the user further

**ARTICLE**:  
NATO is no longer hiding that it is gearing up for a potential military conflict with Russia, Deputy Foreign Minister Aleksandr Grushko has said, pointing to this year's Steadfast Defender drills, the bloc's largest maneuvers since the end of the Cold War. 
The US-led military bloc has been expanding eastward for decades, despite assurances given to the Soviet Union in the run-up to German reunification in 1990 that it would not do so. Russia has repeatedly described the expansion toward its borders as a threat to its security. Speaking to RIA Novosti on Tuesday, Grushko said that “now NATO representatives have stopped hiding that they are preparing for a potential armed clash with Russia.” 
He cited the Steadfast Defender exercise that ran from January through late May, saying that “for the first time, the enemy was not a fictitious state, but Russia.” 
While NATO did not specifically name Russia in its announcement of the drills, it called the exercises preparation for a conflict with a “near-peer” adversary. 
NATO’s main security document identifies Russia as the bloc’s largest threat. 

**DETECTED PROPAGANDA**:
{
    "Justification": [
        {
            "explanation": "This passage appeals to shared values and historical context by referencing assurances given to the Soviet Union, suggesting that NATO's actions are a betrayal of trust, which can evoke a sense of injustice and rally support against NATO's expansion.",
            "location": "despite assurances given to the Soviet Union in the run-up to German reunification in 1990 that it would not do so."
        }
    ],
    "Attack on Reputation": [
        {
            "explanation": "This passage casts doubt on NATO's intentions and credibility by implying that it is acting in bad faith, which undermines the organization's reputation and legitimacy.",
            "location": "NATO is no longer hiding that it is gearing up for a potential military conflict with Russia."
        }
    ]
}
"""
    client = OpenAI()
    messages = [{"role": "system", "content": system_prompt}]
    last_audio_id = None
    response_counter = 0
    MESSAGE_LIMIT = 10

    # Start the conversation with an initial text-only user message
    initial_user_message = "Please start the conversation."
    messages.append({"role": "user", "content": [
        { "type": "text", "text": initial_user_message }
    ]})

    # Get the initial assistant response
    completion = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "alloy", "format": "wav"},
        messages=messages
    )
    # Use the assistant audio transcript as instructed
    assistant_response_text = completion.choices[0].message.audio.transcript
    print("\n--- Assistant Text Response ---")
    print(assistant_response_text)

    # Save the assistant's audio response if available
    if completion.choices[0].message.audio:
        last_audio_id = completion.choices[0].message.audio.id
        wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
        response_counter += 1
        filename = f"response_{response_counter}.wav"
        with open(filename, "wb") as f:
            f.write(wav_bytes)
        print(f"Audio response saved as '{filename}'.")

    messages.append({"role": "assistant", "content": assistant_response_text})

    # Set up speech recognition for capturing user's spoken responses
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    # Conversation loop: capture user's speech, convert to WAV, encode, and send as input_audio
    while True:
        print("\nPlease speak your response:")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            audio_data = recognizer.listen(source)
        # try:
        #     # Recognize the speech (for logging purposes)
        #     recognized_text = recognizer.recognize_google(audio_data)
        #     print(f"You said (transcribed): {recognized_text}")
        # except sr.UnknownValueError:
        #     print("Sorry, could not understand your speech. Please try again.")
        #     continue
        # except sr.RequestError as e:
        #     print(f"Speech recognition error: {e}")
        #     continue
        #save the audio to a json file
        # with open("recording_audio_working.json", "wb") as file:
        #     file.write(audio_data)
        # Get the WAV bytes from the captured audio
        wav_bytes = audio_data.get_wav_data()
        with open("audio_working_wav_bytes.json", "wb") as file:
            file.write(wav_bytes)
        # Encode the WAV data to base64 as expected by OpenAI
        encoded_audio = base64.b64encode(wav_bytes).decode('utf-8')
        with open("audio_working.json", "w") as file:
            file.write(encoded_audio)
        # Create a user message containing both text and audio input
        print("type of encoded_audio", type(encoded_audio))
        user_message = {
            "role": "user",
            "content": [
                # { "type": "text", "text": recognized_text },
                { "type": "input_audio", "input_audio": {
                    "data": encoded_audio,
                    "format": "wav"
                } }
            ]
        }
        messages.append(user_message)

        # Keep conversation history within the defined message limit (preserve the system prompt)
        if len(messages) > MESSAGE_LIMIT + 1:
            messages = [messages[0]] + messages[-MESSAGE_LIMIT:]

        # If a previous audio response exists, include its audio id for continuity
        if last_audio_id:
            messages.append({"role": "assistant", "audio": {"id": last_audio_id}})

        # Request the next assistant response with the updated messages
        
        #save messages to a json file
        import json
        with open('messages_working.json', 'w') as f:
            json.dump(messages, f)
        completion = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=messages
        )
        assistant_response_text = completion.choices[0].message.audio.transcript
        print("\n--- Assistant Text Response ---")
        print(assistant_response_text)

        # Save the new assistant audio response if available
        if completion.choices[0].message.audio:
            last_audio_id = completion.choices[0].message.audio.id
            wav_bytes = base64.b64decode(completion.choices[0].message.audio.data)
            response_counter += 1
            filename = f"response_{response_counter}.wav"
            with open(filename, "wb") as f:
                f.write(wav_bytes)
            print(f"Audio response saved as '{filename}'.")

        messages.append({"role": "assistant", "content": assistant_response_text})

if __name__ == "__main__":
    asyncio.run(main())
