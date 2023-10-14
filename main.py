from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
import openai
import vlc
from google.cloud import texttospeech
import os
import requests
import subprocess
import json

# Create a new peer connection instance
pc = RTCPeerConnection()
# Global data channel to communicate with frontend
global_data_channel = None

# Define routes
routes = web.RouteTableDef()


# Serve the frontend index.html file
@routes.get('/')
async def index(request):
    return web.FileResponse('index.html')


# Handle WebRTC offers
@routes.post('/offer')
async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(content_type='application/json', text=json.dumps({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }))


# Event handler for data channels
async def on_datachannel(channel):
    global global_data_channel
    global_data_channel = channel
    channel.on('message', on_message)


# Sample on_message handler (you can customize it based on your use case)
async def on_message(message):
    print("Received message:", message)
    # Here, you would typically use OpenAI to generate a response
    ai_response = "This is an AI response to your message."  # Placeholder
    global_data_channel.send(ai_response)


pc.on('datachannel', on_datachannel)

FIFO = "my_fifo"

if not os.path.exists(FIFO):
    os.mkfifo(FIFO)

# VLC and API setup
os.environ["DYLD_LIBRARY_PATH"] = "/Applications/VLC.app/Contents/MacOS/lib/"
openai.api_key = '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'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/Zachc57/PycharmProjects/pythonProject/venv/myKey.json'
DEEP_AI_API_KEY = 'acca39c7-2279-4b6a-99b3-147a369e4f92'  # Replace with your DeepAI API key

# Initialize Google Text-to-Speech client
client = texttospeech.TextToSpeechClient()


def play_video(filename):
    player = vlc.MediaPlayer(filename)
    player.play()
    while player.is_playing():
        pass


def text_to_audio(text, voice_type="neutral"):
    # Define the voice based on the voice type
    voice_parameters = {
        "neutral": {
            "language_code": "en-US",
            "name": "en-US-Wavenet-A",
            "ssml_gender": texttospeech.SsmlVoiceGender.NEUTRAL
        },
        "female_us": {
            "language_code": "en-US",
            "name": "en-US-Wavenet-F",
            "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE
        },
        "male_us": {
            "language_code": "en-US",
            "name": "en-US-Wavenet-D",
            "ssml_gender": texttospeech.SsmlVoiceGender.MALE
        },
        "male_uk": {
            "language_code": "en-GB",
            "name": "en-GB-Wavenet-D",
            "ssml_gender": texttospeech.SsmlVoiceGender.MALE
        }
    }

    voice = voice_parameters.get(voice_type, voice_parameters["neutral"])

    synthesis_input = texttospeech.SynthesisInput(text=text)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3.value)

    # Call the Google Text-to-Speech API
    try:
        response_audio = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

        # Save the audio response to a file
        audio_filename = 'response.mp3'
        with open(audio_filename, 'wb') as out:
            out.write(response_audio.audio_content)
        return audio_filename
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None


def split_into_paragraphs(text):
    return [para.strip() for para in text.split("\n") if para.strip() != ""]


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
    audio_filename = text_to_audio(text, voice_type)
    img_filename = generate_image_from_text(text)

    video_filename = "output_video.mp4"

    cmd = [
        'ffmpeg',
        '-loop', '1',
        '-i', img_filename,
        '-i', audio_filename,
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-f', 'mpegts',  # Set the output format to MPEG transport stream
        'udp://127.0.0.1:12345'  # Send the output to UDP port 12345
    ]

    subprocess.run(cmd)

    os.remove(img_filename)
    os.remove(audio_filename)

    return video_filename


def ai_meeting(topic):
    ai_count = int(input("Enter the number of AIs you want in the meeting: "))

    # Setting the voice for each AI
    available_voices = ["female_us", "male_us", "male_uk"]
    participants = [{"role": "user", "name": "User"}]

    for i in range(ai_count):
        ai_name = f"AI-{i + 1}"
        expertise = input(f"Enter the expertise for {ai_name}: ")
        voice = available_voices[i % len(available_voices)]
        participants.append({"role": "assistant", "name": ai_name, "expertise": expertise, "voice": voice})

    for idx, participant in enumerate(participants):
        print(f"{idx + 1}. {participant['name']}")
    leader_idx = int(input("Who should lead the meeting? (Enter the number): ")) - 1
    leader = participants[leader_idx]['name']

    leader_info = participants.pop(leader_idx)
    participants.insert(1, leader_info)

    messages = []

    if leader == "User":
        initial_message = input("You are leading the meeting. Start the conversation: ")
        messages.append({"role": "user", "content": initial_message})
    else:
        initial_message = f"{leader} initiates a conversation about {topic}."
        messages.append({"role": "assistant", "content": initial_message})

    print(f"\n[Meeting on {topic}]\n")

    # Setting up the FFmpeg process for live video generation
    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite existing file if it exists
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg',
        '-r', '24',  # 24 frames per second
        '-i', '-',  # Read from stdin
        '-i', 'live_output_audio.aac',  # Use the live audio file we'll be updating
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-c:a', 'aac',
        'live_output.mp4'
    ]

    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

    for _ in range(5):
        for participant in participants:
            if participant['role'] == 'user':
                continue

            expertise_prompt = f"As a {participant['expertise']}, considering the insights from {leader}, how can we " \
                               f"further understand and expand upon the topic?"
            messages[-1]['content'] += f" {expertise_prompt}"

            try:
                response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                statement = response['choices'][0]['message']['content'].strip()

                video_clip = generate_clip_from_text(statement, participant['voice'])

                with open(video_clip, 'rb') as video_file:
                    ffmpeg_process.stdin.write(video_file.read())

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

    # Once all clips are generated
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()

    # Play the live-generated video
    play_video('live_output.mp4')


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app)  # This starts the aiohttp server and will run indefinitely
