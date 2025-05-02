import streamlit as st
import os
from pytube import YouTube
from moviepy.editor import AudioFileClip
import speech_recognition as sr
import tempfile

def download_audio(url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "audio.mp4")
        audio_stream.download(output_path=temp_dir, filename="audio.mp4")
        return audio_path
    except Exception as e:
        st.error(f"Error downloading audio: {str(e)}")
        return None

def convert_to_wav(audio_path):
    try:
        audio = AudioFileClip(audio_path)
        wav_path = audio_path.replace(".mp4", ".wav")
        audio.write_audiofile(wav_path)
        audio.close()
        return wav_path
    except Exception as e:
        st.error(f"Error converting to WAV: {str(e)}")
        return None

def transcribe_audio(wav_path):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

def main():
    st.title("YouTube Transcript Generator")
    st.write("Enter a YouTube URL to generate its transcript")
    
    url = st.text_input("YouTube URL")
    
    if st.button("Generate Transcript"):
        if url:
            with st.spinner("Downloading audio..."):
                audio_path = download_audio(url)
                if audio_path:
                    with st.spinner("Converting to WAV..."):
                        wav_path = convert_to_wav(audio_path)
                        if wav_path:
                            with st.spinner("Generating transcript..."):
                                transcript = transcribe_audio(wav_path)
                                if transcript:
                                    st.success("Transcript generated successfully!")
                                    st.text_area("Transcript", transcript, height=300)
                                    
                                    # Cleanup temporary files
                                    try:
                                        os.remove(audio_path)
                                        os.remove(wav_path)
                                        os.rmdir(os.path.dirname(audio_path))
                                    except:
                                        pass
        else:
            st.warning("Please enter a YouTube URL")

if __name__ == "__main__":
    main() 