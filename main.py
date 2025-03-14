import whisper
from pyaudio import PyAudio, paInt16
import numpy as np
import torch
import tkinter as tk
import subprocess
from threading import Thread
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from g4f.client import Client
from gtts import gTTS
import os

class SpeechRec:
    is_on = False
    def __init__(self, root):
        self.root = root

        #Premi per parlare
        self.button = tk.Button(root, text="Premi per parlare", bg="green", fg="white")
        self.button.bind("<Button-1>", self.start)
        self.button.bind("<ButtonRelease-1>", self.stop)
        self.button.grid(row=0, column=0, columnspan=2, sticky="nsew")

        #Carica mp3
        self.button2 = tk.Button(root, text="Scegli MP3", bg="orange", fg="white")
        self.button2.bind("<Button-1>", self.music)
        self.button2.grid(row=3, column=0, columnspan=2, sticky="nsew")

        #Display cosa capisce
        self.label = tk.Label(root, text="", bg="black", fg="white")
        self.label.grid(row=1, column=0, columnspan=2, sticky="nsew")

        #Display result
        self.output_text_frame = tk.Frame(root, bg="black")
        self.output_text_frame.grid(row=5, column=0, columnspan=2, sticky="nsew")

        #switch voice
        self.button3= tk.Button(root,text="Voice off",bg="red",fg="white")
        self.button3.bind("<Button-1>",self.voice)
        self.button3.grid(row=2, column=0, columnspan=2, sticky="nsew")

        # Progress bar
        self.progress = ttk.Progressbar(root, orient="horizontal", mode="indeterminate")
        self.progress.grid(row=4, column=0, columnspan=2, sticky="nsew")

        root.grid_rowconfigure(0, weight=0)
        root.grid_rowconfigure(1, weight=0)
        root.grid_rowconfigure(2, weight=0)
        root.grid_rowconfigure(3, weight=0)
        root.grid_rowconfigure(4, weight=0)
        root.grid_rowconfigure(5, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

        # Audio setup
        self.model = whisper.load_model("turbo")
        self.audio = PyAudio()
        self.stream = None
        self.recording = False
        self.audio_data = np.array([], dtype=np.int16)

    def voice(self,event):
        if self.is_on==False:
            self.button3['text']="Voice on"
            print("Sono on")
            self.is_on=True
        else:
            self.button3['text']="Voice off"
            print("Sono off")
            self.is_on=False

    def music(self, event):
        self.progress.start(10)
        thread = Thread(target=self.process_music)
        thread.start()

    def process_music(self):
        fn = askopenfilename()
        if not fn:
            self.root.after(0, self.progress.stop)
            return

        print(f"📂 File selezionato: {fn}")  # DEBUG

        result = self.model.transcribe(fn)
        text = result["text"]

        print(f"✅ Testo trascritto: {text}")  # DEBUG

        # Aggiorna la GUI nel thread principale
        self.root.after(0, self.display_text, text)

    def display_text(self, text):
        self.progress.stop()

        # Pulisce il frame prima di aggiungere il nuovo testo
        for widget in self.output_text_frame.winfo_children():
            widget.destroy()

        # Controllo se il testo è vuoto
        if not text.strip():
            print("❌ Nessun testo trascritto!")  # DEBUG
            return

        print("📝 Aggiungo il testo alla GUI...")  # DEBUG
        print(text)
        # Creazione di un widget Text con scrollbar per gestire il testo lungo
        text_widget = tk.Text(self.output_text_frame, wrap="word", bg="black", fg="white", font=("Arial", 12))
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")  # Rende il testo non modificabile
        text_widget.pack(fill="both", expand=True, padx=10, pady=2)

        # Aggiunge una scrollbar verticale per il testo
        scrollbar = tk.Scrollbar(self.output_text_frame, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)

    def start(self, event):
        self.button.config(text="Speaking...")
        self.stream = self.audio.open(format=paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        self.recording = True
        thread = Thread(target=self.record_audio)
        thread.start()

    def record_audio(self):
        while self.recording:
            data = np.frombuffer(self.stream.read(1024), dtype=np.int16)
            self.audio_data = np.append(self.audio_data, data)

        self.stream.stop_stream()
        self.stream.close()
        self.transcribe_audio()

    def transcribe_audio(self):
        audio_data_float = self.audio_data / (2**15 - 1)
        result = self.model.transcribe(torch.from_numpy(audio_data_float).float(), language="it")
        text = result["text"]

        print(f"🎙 Testo parlato trascritto: {text}")  # DEBUG
        self.label.config(text=f"Tu: {text}")
        
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{text}"}],
            web_search=False
        )
        self.display_text(response.choices[0].message.content)
        if self.is_on:
            thread = Thread(target=self.speak, args=(response.choices[0].message.content,))
            thread.start()

        self.audio_data = np.array([], dtype=np.int16)
    #Funzione per leggere
    def speak(self, text):
        file = "file.mp3"
        tts = gTTS(text, lang='it', tld="it")
        tts.save(file)
        print("✅ Audio generato, avvio riproduzione...")
        os.system(f'ffmpeg -i {file} -filter:a "atempo=1.3" -vn -f wav - | ffplay -nodisp -autoexit -')

    def stop(self, event):
        self.button.config(text="Premi per parlare")
        self.recording = False


def main():
    root = tk.Tk()
    root.geometry("960x540")
    root.configure(bg="black")
    app = SpeechRec(root)
    root.mainloop()


if __name__ == "__main__":
    main()
