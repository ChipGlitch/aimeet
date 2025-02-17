import openai
import vlc
from google.cloud import texttospeech
from moviepy.editor import *
from PIL import Image
import os
import requests

# VLC and API setup
os.environ["DYLD_LIBRARY_PATH"] = "/Applications/VLC.app/Contents/MacOS/lib/"
openai.api_key = 'private'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/Zachc57/PycharmProjects/pythonProject/venv/myKey.json'
DEEP_AI_API_KEY = 'private'  

# Initialize Google Text-to-Speech client
client = texttospeech.TextToSpeechClient()


def play_video(filename):
    player = vlc.MediaPlayer(filename)
    player.play()
    while player.is_playing():
        pass


def text_to_audio(text, voice_type="neutral"):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    if voice_type == "female_us":
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Wavenet-F",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
    elif voice_type == "male_us":
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Wavenet-D",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
    elif voice_type == "male_uk":
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-GB",
            name="en-GB-Wavenet-D",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
# Randomize voice -TODO
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response_audio = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    audio_filename = 'response.mp3'
    with open(audio_filename, 'wb') as out:
        out.write(response_audio.audio_content)
    return audio_filename


def split_into_paragraphs(text):
    return [para.strip() for para in text.split("\n") if para.strip() != ""]

#witch between avatar/pictures

def generate_image_from_text(text):
    response = requests.post(
        "https://api.deepai.org/api/text2img",
        headers={"api-key": DEEP_AI_API_KEY},
        data={"text": text}
    )

    try:
        image_url = response.json()["output_url"]
        image_filename = "generated_image.jpg"
        image_content = requests.get(image_url).content
        with open(image_filename, 'wb') as file:
            file.write(image_content)
        return image_filename
    except KeyError:
        print("Error: Could not fetch the image URL from the API response.")
        return None


def generate_clip_from_text(text, voice_type):
    paragraphs = split_into_paragraphs(text)
    audio_filename = text_to_audio(text, voice_type)

    image_filenames = []
    for paragraph in paragraphs:
        img_filename = generate_image_from_text(paragraph)
        if img_filename:
            image_filenames.append(img_filename)

    duration = len(text) * 0.08  # Assuming a reading speed of about 125 words per minute
    clips = [ImageClip(filename).set_duration(duration) for filename in image_filenames]
    concatenated_clip = concatenate_videoclips(clips, method="compose")
    audioclip = AudioFileClip(audio_filename)
    videoclip = concatenated_clip.set_audio(audioclip)

    for image_filename in image_filenames:
        if os.path.exists(image_filename):
            os.remove(image_filename)

    return videoclip


def generate_final_video(clips):
    final_clip = concatenate_videoclips(clips, method="compose")
    video_filename_input = input("Enter a name for the video (without extension): ")
    video_filename = f"{video_filename_input}.mp4"

    final_clip.fps = 24
    final_clip.write_videofile(video_filename, audio_codec='aac')
    return video_filename


def ai_meeting(topic):
    # Get number of AIs from the user
    ai_count = int(input("Enter the number of AIs you want in the meeting: "))

    # Setting the voice for each AI
    available_voices = ["female_us", "male_us", "male_uk"]
    participants = [{"role": "user", "name": "User"}]  # Include the user as the first participant

    for i in range(ai_count):
        ai_name = f"AI-{i + 1}"
        expertise = input(f"Enter the expertise for {ai_name}: ")
        voice = available_voices[i % len(available_voices)]
        participants.append({"role": "assistant", "name": ai_name, "expertise": expertise, "voice": voice})

    # Choose the leader
    for idx, participant in enumerate(participants):
        print(f"{idx + 1}. {participant['name']}")
    leader_idx = int(input("Who should lead the meeting? (Enter the number): ")) - 1
    leader = participants[leader_idx]['name']

    messages = []

    if leader == "User":
        initial_message = input("You are leading the meeting. Start the conversation: ")
        messages.append({"role": "user", "content": initial_message})
    else:
        initial_message = f"{leader} initiates a conversation about {topic}."
        messages.append({"role": "assistant", "content": initial_message})

    print(f"\n[Meeting on {topic}]\n")

    clips = []

    for _ in range(5):
        for participant in participants:
            if participant['role'] == 'user':
                continue

            expertise_prompt = f"As a {participant['expertise']}, considering the insights from {leader}, how can we further understand and expand upon the topic?"
            messages[-1]['content'] += f" {expertise_prompt}"

            try:
                response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                statement = response['choices'][0]['message']['content'].strip()

                video_clip = generate_clip_from_text(statement, participant['voice'])
                clips.append(video_clip)

                print(f"{participant['name']} ({participant['expertise']}): {statement}\n")

                messages.append({"role": "assistant", "content": statement})
            except openai.error.OpenAIError as e:
                print(f"Error: {e}")
                return

        user_input = input("Your turn (type 'skip' to let the AIs continue, 'end' to conclude the meeting): ")

        if user_input.lower() == 'end':
            print("Meeting concluded by the user.")
            break
        elif user_input.lower() != 'skip':
            print(f"You: {user_input}\n")
            messages.append({"role": "user", "content": user_input})

    final_video_filename = generate_final_video(clips)
    play_video(final_video_filename)


if __name__ == "__main__":
    meeting_topic = input("Enter the topic for the meeting: ")
    ai_meeting(meeting_topic)

# PYQT for GUI. Sends text to text box underneath where user enters info. Generates live video and saves video aftewards.
# https://www.d-id.com/api/?utm_term=ai%20avatar%20api&utm_campaign=API&utm_source=adwords&utm_medium=ppc&hsa_acc=6149207258&hsa_cam=19663081091&hsa_grp=146356427216&hsa_ad=670131118949&hsa_src=g&hsa_tgt=kwd-1926918698331&hsa_kw=ai%20avatar%20api&hsa_mt=p&hsa_net=adwords&hsa_ver=3&gad_source=1&gclid=CjwKCAjw9-6oBhBaEiwAHv1QvDGcpA1abNL4uxMRm4bFOHapUVRg_yyH0J0HErT9JcPfJCCyG-hB5BoCmQEQAvD_BwE
#let them name AI so it's not like input from A1-1
# fix video speech timing
# uses: multi person presentations with input from user and the rest AI. 2) picture book/ script generator with multiple AI 3) business think tank 
