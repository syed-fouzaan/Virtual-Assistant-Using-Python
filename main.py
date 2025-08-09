# Voice Assistant with GUI, Memory, GPT-like Chat, Command Execution, and TTS
# Includes real-time wake-word detection, voice-based interaction, audio upload from web, memory export, and GUI integration

import sys
import os
import threading
import datetime
import csv
import pyttsx3
import speech_recognition as sr
import pvporcupine
import pyaudio
import openai
from openai import OpenAI
import json
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit,
                             QPushButton, QLabel, QFileDialog, QLineEdit, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt

# Load your OpenAI API key
client = OpenAI(api_key="YOUR OPENAI API")

# Voice Engine Setup
engine = pyttsx3.init()
def speak(text):
    engine.say(text)
    engine.runAndWait()

# Memory System
MEMORY_FILE = "memory.json"
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

memory = load_memory()

def remember(convo):
    memory.append(convo)
    save_memory(memory)

def export_memory_to_csv():
    with open('memory.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["User", "Assistant"])
        for item in memory:
            writer.writerow([item['user'], item['assistant']])

# GPT-like Response Generator
def chat_with_gpt(prompt):
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]
    for item in memory[-10:]:
        conversation.append({"role": "user", "content": item['user']})
        conversation.append({"role": "assistant", "content": item['assistant']})
    conversation.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=conversation)
    return response['choices'][0]['message']['content']

# Recognize Voice
recognizer = sr.Recognizer()
def recognize_speech_from_mic():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I didn't catch that."
    except sr.RequestError:
        return "Could not request results."

# Execute Commands
import webbrowser

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def start_flask_app():
    app.run(debug=True, use_reloader=False)

def execute_command(cmd):
    cmd = cmd.lower()
    if "open browser" in cmd:
        webbrowser.open("https://google.com")
        return "Opened browser."
    elif "play music" in cmd:
        os.system("start wmplayer")
        return "Playing music."
    elif "what is the time" in cmd:
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}"
    else:
        return None

# Wake Word Thread
class WakeWordThread(threading.Thread):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.running = True

    def run(self):
        access_key = "YOUR PICOVOICE ACCESS KEY" # Picovoice AccessKey
        porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        while self.running:
            pcm = stream.read(porcupine.frame_length)
            pcm = list(int.from_bytes(pcm[i:i+2], byteorder='little', signed=True) for i in range(0, len(pcm), 2))
            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                self.callback()
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

    def stop(self):
        self.running = False

# GUI Class
class VoiceAssistantGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Assistant with Memory")
        self.setGeometry(100, 100, 600, 500)

        self.layout = QVBoxLayout()
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type a message or speak...")
        self.send_btn = QPushButton("Send")
        self.voice_btn = QPushButton("🎙 Speak")
        self.export_btn = QPushButton("Export Memory")

        row = QHBoxLayout()
        row.addWidget(self.user_input)
        row.addWidget(self.send_btn)
        row.addWidget(self.voice_btn)

        self.layout.addWidget(QLabel("Chat History:"))
        self.layout.addWidget(self.chat_history)
        self.layout.addLayout(row)
        self.layout.addWidget(self.export_btn)
        self.setLayout(self.layout)

        self.send_btn.clicked.connect(self.handle_input)
        self.voice_btn.clicked.connect(self.handle_voice)
        self.export_btn.clicked.connect(export_memory_to_csv)

        self.wake_thread = WakeWordThread(self.wake_triggered)
        self.wake_thread.start()

    def append_chat(self, user, assistant):
        self.chat_history.append(f"👤 {user}")
        self.chat_history.append(f"🤖 {assistant}\n")

    def handle_input(self):
        text = self.user_input.text().strip()
        if text:
            self.user_input.clear()
            self.process_message(text)

    def handle_voice(self):
        query = recognize_speech_from_mic()
        self.process_message(query)

    def process_message(self, msg):
        response = execute_command(msg)
        if not response:
            response = chat_with_gpt(msg)
        self.append_chat(msg, response)
        remember({'user': msg, 'assistant': response})
        speak(response)

    def wake_triggered(self):
        self.handle_voice()

    def closeEvent(self, event):
        self.wake_thread.stop()
        event.accept()

if __name__ == '__main__':
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.daemon = True # Allow the main program to exit even if the thread is still running
    flask_thread.start()

    app = QApplication(sys.argv)
    window = VoiceAssistantGUI()
    window.show()
    sys.exit(app.exec_())
