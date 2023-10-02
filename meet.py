import openai
import os
from google.cloud import texttospeech
import pygame

# Set up your API key
openai.api_key = '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'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/Zachc57/PycharmProjects/pythonProject/venv/myKey.json'
client = texttospeech.TextToSpeechClient()

# Define voices for each AI
AI_VOICES = {
    "AI-0": "en-US-Wavenet-A",
    "AI-1": "en-US-Wavenet-D",
    "AI-2": "en-US-Wavenet-F",
}

def play_audio(filename):
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def play_response_with_tts(text, voice_name):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response_audio = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    audio_filename = 'response.mp3'
    with open(audio_filename, 'wb') as out:
        out.write(response_audio.audio_content)

    play_audio(audio_filename)

def ai_meeting(topic, ai_count=3, leader="user"):
    roles = ["Sensing and Perception Expert", "Autonomous Navigation Specialist", "Collaborative Robotics Expert"]
    participants = [{"role": "assistant", "name": f"AI-{i}", "expertise": roles[i]} for i in range(ai_count)]
    messages = []

    if leader == "user":
        initial_message = input("You are leading the meeting. Start the conversation: ")
        messages.append({"role": "user", "content": initial_message})
    else:
        initial_message = f"{leader} initiates a conversation about {topic}."
        messages.append({"role": "assistant", "content": initial_message})

    print(f"\n[Meeting on {topic}]\n")

    for _ in range(5):
        for participant in participants:
            expertise_prompt = f"As a {participant['expertise']}, considering previous insights, how can we further understand and expand upon the topic?"
            messages[-1]['content'] += f" {expertise_prompt}"

            try:
                response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                statement = response['choices'][0]['message']['content'].strip()

                print(f"{participant['name']} ({participant['expertise']}): {statement}\n")
                play_response_with_tts(statement, AI_VOICES[participant['name']])
                messages.append({"role": "assistant", "content": statement})
            except openai.error.OpenAIError as e:
                print(f"Error: {e}")
                return

        user_input = input("Your turn (or type 'skip' to let the AIs continue): ")
        if user_input.lower() != "skip":
            print(f"You: {user_input}\n")
            messages.append({"role": "user", "content": user_input})

if __name__ == "__main__":
    meeting_topic = input("Enter the topic for the meeting: ")
    leader_choice = input("Who should lead the meeting (user/AI-1/AI-2/etc.): ")

    ai_meeting(meeting_topic, leader=leader_choice)
