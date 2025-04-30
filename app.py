import streamlit as st
import os
import logging
from dotenv import load_dotenv
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure page layout and theme
st.set_page_config(
    page_title="YouTube Video Summarizer",
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

# Add cache for transcript fetching
@st.cache_data(ttl=3600)  # Cache for 1 hour
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

# Custom CSS for enhanced theme and layout
st.markdown("""
    <style>
        /* Main App Background with Gradient */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
        }
        
        /* Title Styling */
        .title-wrapper {
            background: linear-gradient(90deg, #3b82f6, #2563eb);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
        }
        
        /* Card-like containers */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(45, 45, 45, 0.2);
            padding: 10px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 10px 20px;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, #3b82f6, #2563eb);
            border: none;
        }
        
        /* Button Styling */
        .stButton>button {
            background: linear-gradient(90deg, #3b82f6, #2563eb);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
            background: linear-gradient(90deg, #2563eb, #1d4ed8);
        }
        
        /* Input Fields */
        .stTextInput>div>div {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            padding: 8px;
        }
        
        /* Video Container */
        .video-container {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            margin: 20px 0;
        }
        
        /* Transcript Container */
        .transcript-box {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid rgba(59, 130, 246, 0.2);
            backdrop-filter: blur(10px);
        }
        
        /* Info Messages */
        .stAlert {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 10px;
            padding: 10px;
        }
        
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(59, 130, 246, 0.5);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(59, 130, 246, 0.7);
        }
        
        /* Loading Spinner */
        .stSpinner > div {
            border-color: #3b82f6 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Wrap title in custom div
st.markdown('<div class="title-wrapper"><h1>YouTube Video Summarizer</h1></div>', unsafe_allow_html=True)

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
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception as e:
            logger.error(f"Transcript list error: {str(e)}")
            st.error(
                "Could not retrieve a transcript for this video. "
                "This can happen even if subtitles are visible on YouTube, due to copyright, region, or YouTube restrictions. "
                "Please try another video."
            )
            return None

        transcript = None
        original_lang = None

        # Try manual transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(
                ['en', 'hi', 'mr', 'es', 'fr', 'de', 'ja', 'ko', 'ru']
            )
            original_lang = transcript.language_code
        except Exception:
            # Try auto-generated transcript
            try:
                transcript = transcript_list.find_generated_transcript(
                    ['en', 'hi', 'mr', 'es', 'fr', 'de', 'ja', 'ko', 'ru']
                )
                original_lang = transcript.language_code
            except Exception:
                st.error(
                    "No transcript available for this video in the supported languages. "
                    "Please try another video."
                )
                return None

        # Try translation if needed
        if target_lang != original_lang:
            try:
                transcript = transcript.translate(target_lang)
            except Exception:
                st.warning(f"Could not translate to {target_lang}. Using original language.")

        # Fetch and combine transcript text
        try:
            transcript_parts = transcript.fetch()
            text_parts = []
            for part in transcript_parts:
                if isinstance(part, dict) and 'text' in part:
                    text_parts.append(part['text'])
                elif hasattr(part, 'text'):
                    text_parts.append(part.text)
            full_text = ' '.join(text_parts)
            if not full_text:
                st.error("Transcript is empty. Please try another video.")
                return None
            return {
                'text': full_text,
                'original_language': original_lang
            }
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            st.error("Transcript could not be processed. Please try another video.")
            return None

    except Exception as e:
        logger.error(f"Transcript error: {str(e)}")
        st.error("An unexpected error occurred while fetching the transcript. Please try another video.")
        return None

# Main app layout
st.title("YouTube Video Summarizer")

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
                            st.write(summary)
                    except Exception as e:
                        logger.error(f"Error in summary generation: {str(e)}")
                        st.error("An error occurred while generating the summary. Please try again.")
            
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
                            st.write(chat_completion.choices[0].message.content)
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")

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
                        st.write(transcript_data['text'])
            except Exception as e:
                st.error(f"An error occurred while fetching transcript: {str(e)}")

    except IndexError:
        st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")


