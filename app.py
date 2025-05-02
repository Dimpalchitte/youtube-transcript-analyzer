import streamlit as st
import os
import logging
from dotenv import load_dotenv
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
import base64
from gtts import gTTS
import io
import time
from functools import wraps

# --- gTTS Helper ---
def tts_audio(text, lang='en'):
    tts = gTTS(text, lang=lang)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# Configure logging to file instead of console
logging.basicConfig(
    filename='app.log',  # Log to file instead of console
    level=logging.ERROR,  # Only log errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure page layout and theme
st.set_page_config(
    page_title="YouTube Transcript Analyzer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add deployment configuration
@st.cache_resource
def get_groq_client():
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        return Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Error initializing Groq client: {str(e)}")
        st.error("Failed to initialize AI service. Please check your API key and try again.")
        st.stop()

# Initialize Groq client
client = get_groq_client()

# Add retry decorator
def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# Add cache for transcript fetching with longer TTL
@st.cache_data(ttl=7200)  # Cache for 2 hours
def get_cached_transcript(url, target_lang='en'):
    return get_transcript(url, target_lang)

# Add cache for summary generation
@st.cache_data(ttl=3600)
def generate_cached_summary(transcript_text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates detailed summaries of YouTube videos."},
                {"role": "user", "content": f"{prompt}\n\n{transcript_text}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2000
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise

# Custom CSS with fixed input text visibility and clean design
st.markdown("""
    <style>
        /* Main Background */
        .stApp {
            background: #fff0f3;
        }
        
        /* Ensure all text has proper contrast */
        .stMarkdown, .stMarkdown p, .stMarkdown li {
            color: #1a1a1a !important;
        }
        
        /* Make sure headers and text are clearly visible */
        h1, h2, h3, h4, h5, h6, p, li, span {
            color: #1a1a1a !important;
        }

        /* Input field styling with visible text */
        .stTextInput>div>div {
            background-color: white !important;
            border-radius: 8px;
            border: 2px solid #ffb3c1 !important;
            padding: 8px;
        }

        /* Make input text clearly visible */
        .stTextInput input, .stTextArea textarea {
            color: black !important;
            font-size: 16px !important;
            font-weight: 400 !important;
            background-color: white !important;
        }
        /* Ensure blinking caret is visible */
        input, textarea {
            caret-color: #1a1a1a !important;
        }

        /* Style the placeholder text */
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {
            color: #666 !important;
            opacity: 1 !important;
        }

        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px !important;
            padding: 10px 15px;
            background-color: #ffe5e9;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 10px 20px;
            background-color: #ffb3c1;
            border-radius: 8px;
            margin-right: 10px;
            border: none;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #ff8fa3;
        }

        /* Button Styling */
        .stButton>button {
            background-color: #ff4d6d;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            margin: 10px 0;
            transition: none !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stButton>button:hover {
            background-color: #ff758f;
            border: none;
            color: white;
        }

        /* Hide streamlit default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Hide logger messages */
        .stException, .stError, .stWarning {
            display: none !important;
        }

        /* Question input area specific styling */
        [data-testid="stTextArea"] textarea {
            color: black !important;
            background-color: white !important;
            border: 2px solid #ffb3c1 !important;
        }

        /* Add some spacing between elements */
        .block-container {
            padding-top: 1rem;
        }

        /* Make success/info/warning messages more compact */
        .stSuccess, .stInfo, .stWarning {
            padding: 0.5rem !important;
            margin-bottom: 0.5rem !important;
            font-size: 0.9rem !important;
            line-height: 1.2 !important;
        }
        
        /* Reduce the size of the success/info icons */
        .stSuccess svg, .stInfo svg, .stWarning svg {
            height: 1.2rem !important;
            width: 1.2rem !important;
            margin-right: 0.5rem !important;
        }

        /* Base select box styling */
        .stSelectbox > div > div[data-baseweb="select"] {
            background-color: white;
        }

        /* Dropdown menu container */
        div[data-baseweb="popover"] > div {
            background-color: white !important;
            color: #1a1a1a !important;
            border: 1px solid #ffb3c1 !important;
            border-radius: 4px;
        }

        /* Dropdown menu options */
        div[data-baseweb="popover"] ul {
            background-color: white !important;
            color: #1a1a1a !important;
        }

        /* Individual dropdown options */
        div[data-baseweb="popover"] li {
            background-color: white !important;
            color: #1a1a1a !important;
        }

        /* Hover state for dropdown options */
        div[data-baseweb="popover"] li:hover {
            background-color: #ffe5e9 !important;
            color: #1a1a1a !important;
        }

        /* Selected option in dropdown */
        div[data-baseweb="popover"] li[aria-selected="true"] {
            background-color: #ffb3c1 !important;
            color: #1a1a1a !important;
        }

        /* Input field and selected value */
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: white !important;
            color: #1a1a1a !important;
        }

        /* Override any dark backgrounds */
        .stSelectbox div[role="listbox"] {
            background-color: white !important;
        }

        .stSelectbox div[role="option"] {
            background-color: white !important;
            color: #1a1a1a !important;
        }

        /* Ensure text is visible in the select box */
        .stSelectbox [data-testid="stMarkdown"] p {
            color: #1a1a1a !important;
        }
    </style>
""", unsafe_allow_html=True)

# Define the prompt
prompt = """You are an advanced AI specializing in text summarization. Your task is to generate a structured and detailed summary of a YouTube transcript.

Instructions:
1. Extract all key points, facts, and relevant details
2. Provide a well-organized, structured summary
3. Use clear and engaging language
4. Focus on the main topics and important information
5. Be concise but comprehensive
6. Avoid repetition
7. Do not include any reasoning steps or self-reflections
8. Do not mention sponsorships or brand names
9. End with "Have a nice day!"

Output Format:
1. Summary: A clear overview of the main topics
2. Key Points: Important facts and details in bullet points
3. Insights: Deep observations and analysis

Now, please summarize the following transcript:"""

# Modify error display functions to be more user-friendly
def show_error(message):
    st.error(message, icon="🚫")

def show_warning(message):
    st.warning(message, icon="⚠️")

def show_success(message):
    st.success(message, icon="✅")

@retry_on_failure(max_retries=3, delay=2)
def get_transcript(url, target_lang='en'):
    try:
        # Handle different YouTube URL formats
        if "youtu.be" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com" in url:
            video_id = url.split("v=")[1].split("&")[0]
        else:
            st.error("Invalid YouTube URL format. Please enter a valid YouTube video URL.")
            return None

        try:
            # First try to get the transcript list
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception as e:
            logger.error(f"Transcript list error: {str(e)}")
            st.error(
                "Could not retrieve a transcript for this video. "
                "This can happen if:\n"
                "1. The video has no captions\n"
                "2. The video is private\n"
                "3. The video has restricted captions\n"
                "4. YouTube's API is temporarily unavailable\n"
                "Please try again in a few moments or try another video."
            )
            return None

        transcript = None
        original_lang = None

        # Try to find a transcript in the preferred language first
        try:
            transcript = transcript_list.find_transcript([target_lang])
            original_lang = target_lang
        except Exception:
            # If preferred language not found, try English
            try:
                transcript = transcript_list.find_transcript(['en'])
                original_lang = 'en'
            except Exception:
                # If English not found, try any available transcript
                try:
                    transcript = transcript_list.find_transcript([])
                    original_lang = transcript.language_code
                except Exception:
                    st.error(
                        "No transcript available for this video in any supported language. "
                        "Please try another video."
                    )
                    return None

        # Try translation if needed and if the target language is different
        if target_lang != original_lang:
            try:
                transcript = transcript.translate(target_lang)
            except Exception as e:
                logger.warning(f"Translation error: {str(e)}")
                st.warning(f"Could not translate to {target_lang}. Using original language ({original_lang}).")

        # Fetch and combine transcript text
        try:
            transcript_parts = transcript.fetch()
            if not transcript_parts:
                st.error("Transcript is empty. Please try another video.")
                return None

            text_parts = []
            for part in transcript_parts:
                if isinstance(part, dict) and 'text' in part:
                    text_parts.append(part['text'].strip())
                elif hasattr(part, 'text'):
                    text_parts.append(part.text.strip())

            full_text = ' '.join(text_parts)
            if not full_text.strip():
                st.error("Transcript is empty. Please try another video.")
                return None

            return {
                'text': full_text,
                'original_language': original_lang
            }
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            st.error("Transcript could not be processed. Please try again in a few moments.")
            return None

    except Exception as e:
        logger.error(f"Transcript error: {str(e)}")
        st.error("An unexpected error occurred while fetching the transcript. Please try again in a few moments.")
        return None

# Main app layout
st.title("YouTube Transcript Analyzer")

url = st.text_input("Enter the URL of the YouTube video")
if url:
    try:
        # Extract video ID and handle different URL formats
        if "youtu.be" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com" in url:
            video_id = url.split("v=")[1].split("&")[0]
        else:
            raise ValueError("Invalid YouTube URL format")

        # Create main layout columns
        left_col, right_col = st.columns([0.65, 0.35])
        
        with left_col:
            # Video player section
            video_embed = f'''
                <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px;">
                    <iframe src="https://www.youtube.com/embed/{video_id}" 
                        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                    </iframe>
                </div>
            '''
            st.markdown(video_embed, unsafe_allow_html=True)
            
            # Transcript section
            st.markdown("### Transcript")
            target_language = st.selectbox(
                "Select transcript language",
                options=['en', 'hi', 'mr', 'es', 'fr', 'de', 'ja', 'ko', 'ru'],
                format_func=lambda x: {
                    'en': 'English', 'hi': 'Hindi', 'mr': 'Marathi',
                    'es': 'Spanish', 'fr': 'French', 'de': 'German',
                    'ja': 'Japanese', 'ko': 'Korean', 'ru': 'Russian'
                }[x]
            )
            
            transcript_container = st.container()
            
        with right_col:
            # Create tabs for AI Notes and AI Chat
            tab1, tab2 = st.tabs(["🤖 AI Notes", "💭 AI Chat"])
            
            with tab1:
                if st.button("Generate Summary", key="summary_btn"):
                    try:
                        with st.spinner("Generating summary..."):
                            transcript_data = get_cached_transcript(url, 'en')
                            if transcript_data is None:
                                st.stop()
                            summary = generate_cached_summary(transcript_data['text'])
                            st.markdown("### AI Summary")
                            st.session_state['summary_text'] = summary
                            st.write(summary)
                    except Exception as e:
                        logger.error(f"Error in summary generation: {str(e)}")
                        show_error("Unable to generate summary. Please try again.")
                # Show Read Aloud button and audio if summary is available
                if 'summary_text' in st.session_state:
                    if st.button("🔊 Read Aloud (Summary)", key="summary_audio"):
                        audio_fp = tts_audio(st.session_state['summary_text'])
                        audio_bytes = audio_fp.read()
                        audio_html = f"""
                        <audio controls autoplay style='width: 100%; margin-top: 10px;'>
                            <source src='data:audio/mp3;base64,{base64.b64encode(audio_bytes).decode()}' type='audio/mp3'>
                            Your browser does not support the audio element.
                        </audio>
                        """
                        st.markdown(audio_html, unsafe_allow_html=True)
                    st.write(st.session_state['summary_text'])
            
            with tab2:
                st.markdown("### Ask AI about the video")
                user_question = st.text_input("Ask a question about the video content")
                if user_question and st.button("Ask AI", key="ask_btn"):
                    with st.spinner("Thinking..."):
                        try:
                            transcript_data = get_transcript(url, 'en')
                            if transcript_data is None:
                                st.stop()
                            chat_prompt = f"Based on this video transcript: {transcript_data['text']}\n\nQuestion: {user_question}\n\nAnswer:"
                            chat_completion = client.chat.completions.create(
                                messages=[{"role": "user", "content": chat_prompt}],
                                model="llama-3.3-70b-versatile",
                            )
                            ai_answer = chat_completion.choices[0].message.content
                            st.markdown("### AI Answer")
                            st.session_state['ai_answer_text'] = ai_answer
                            st.write(ai_answer)
                        except Exception as e:
                            logger.error(f"Q&A error: {str(e)}")  # Log to file
                            show_error("Unable to process your question. Please try again.")
                # Show Read Aloud button and audio if AI answer is available
                if 'ai_answer_text' in st.session_state:
                    if st.button("🔊 Read Aloud (AI Answer)", key="ai_answer_audio"):
                        audio_fp = tts_audio(st.session_state['ai_answer_text'])
                        audio_bytes = audio_fp.read()
                        audio_html = f"""
                        <audio controls autoplay style='width: 100%; margin-top: 10px;'>
                            <source src='data:audio/mp3;base64,{base64.b64encode(audio_bytes).decode()}' type='audio/mp3'>
                            Your browser does not support the audio element.
                        </audio>
                        """
                        st.markdown(audio_html, unsafe_allow_html=True)
                    st.write(st.session_state['ai_answer_text'])

        # Show transcript in the left column container
        if st.button("Get Transcript", key="transcript_btn"):
            try:
                with transcript_container:
                    with st.spinner("Fetching transcript..."):
                        transcript_data = get_cached_transcript(url, target_language)
                        if transcript_data is None:
                            st.stop()
                        st.info(f"Original video language detected: {transcript_data['original_language']}")
                        st.markdown("### Video Transcription")
                        st.session_state['transcript_text'] = transcript_data['text']
                        st.write(transcript_data['text'])
            except Exception as e:
                st.error(f"An error occurred while fetching transcript: {str(e)}")
        # Show Read Aloud button and audio if transcript is available
        if 'transcript_text' in st.session_state:
            # Read Aloud button at the top
            if st.button("🔊 Read Aloud (Transcript)", key="transcript_audio"):
                audio_fp = tts_audio(st.session_state['transcript_text'])
                audio_bytes = audio_fp.read()
                audio_html = f"""
                <audio controls autoplay style='width: 100%; margin-top: 10px;'>
                    <source src='data:audio/mp3;base64,{base64.b64encode(audio_bytes).decode()}' type='audio/mp3'>
                    Your browser does not support the audio element.
                </audio>
                """
                st.markdown(audio_html, unsafe_allow_html=True)
            # Always show the transcript text once
            st.write(st.session_state['transcript_text'])

    except IndexError:
        st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")


