import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai
import yt_dlp
from PIL import Image
import io
import requests
from langdetect import detect

# ------------------ CONFIG ------------------ #
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Language mapping dictionary (abbreviated for space - include all languages from your original)
LANGUAGE_MAP = {
    'ab': 'Abkhazian', 'aa': 'Afar', 'af': 'Afrikaans', 'ak': 'Akan', 'sq': 'Albanian',
    'am': 'Amharic', 'ar': 'Arabic', 'hy': 'Armenian', 'as': 'Assamese', 'ay': 'Aymara',
    'az': 'Azerbaijani', 'bn': 'Bangla', 'ba': 'Bashkir', 'eu': 'Basque', 'be': 'Belarusian',
    'bho': 'Bhojpuri', 'bs': 'Bosnian', 'br': 'Breton', 'bg': 'Bulgarian', 'my': 'Burmese',
    'ca': 'Catalan', 'ceb': 'Cebuano', 'zh-Hans': 'Chinese (Simplified)', 'zh-Hant': 'Chinese (Traditional)',
    'co': 'Corsican', 'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'dv': 'Divehi',
    'nl': 'Dutch', 'dz': 'Dzongkha', 'en': 'English', 'eo': 'Esperanto', 'et': 'Estonian',
    'ee': 'Ewe', 'fo': 'Faroese', 'fj': 'Fijian', 'fil': 'Filipino', 'fi': 'Finnish',
    'fr': 'French', 'gaa': 'Ga', 'gl': 'Galician', 'lg': 'Ganda', 'ka': 'Georgian',
    'de': 'German', 'el': 'Greek', 'gn': 'Guarani', 'gu': 'Gujarati', 'ht': 'Haitian Creole',
    'ha': 'Hausa', 'haw': 'Hawaiian', 'iw': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong',
    'hu': 'Hungarian', 'is': 'Icelandic', 'ig': 'Igbo', 'id': 'Indonesian', 'iu': 'Inuktitut',
    'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese', 'jv': 'Javanese', 'kl': 'Kalaallisut',
    'kn': 'Kannada', 'kk': 'Kazakh', 'kha': 'Khasi', 'km': 'Khmer', 'rw': 'Kinyarwanda',
    'ko': 'Korean', 'kri': 'Krio', 'ku': 'Kurdish', 'ky': 'Kyrgyz', 'lo': 'Lao',
    'la': 'Latin', 'lv': 'Latvian', 'ln': 'Lingala', 'lt': 'Lithuanian', 'lua': 'Luba-Lulua',
    'luo': 'Luo', 'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay',
    'ml': 'Malayalam', 'mt': 'Maltese', 'gv': 'Manx', 'mi': 'Māori', 'mr': 'Marathi',
    'mn': 'Mongolian', 'mfe': 'Morisyen', 'ne': 'Nepali', 'new': 'Newari', 'nso': 'Northern Sotho',
    'no': 'Norwegian', 'ny': 'Nyanja', 'oc': 'Occitan', 'or': 'Odia', 'om': 'Oromo',
    'os': 'Ossetic', 'pam': 'Pampanga', 'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish',
    'pt': 'Portuguese', 'pt-PT': 'Portuguese (Portugal)', 'pa': 'Punjabi', 'qu': 'Quechua',
    'ro': 'Romanian', 'rn': 'Rundi', 'ru': 'Russian', 'sm': 'Samoan', 'sg': 'Sango',
    'sa': 'Sanskrit', 'gd': 'Scottish Gaelic', 'sr': 'Serbian', 'crs': 'Seselwa Creole French', 
    'sn': 'Shona', 'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian', 
    'so': 'Somali', 'st': 'Southern Sotho', 'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili', 
    'ss': 'Swati', 'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 'tt': 'Tatar', 'te': 'Telugu', 
    'th': 'Thai', 'bo': 'Tibetan', 'ti': 'Tigrinya', 'to': 'Tongan', 'ts': 'Tsonga', 
    'tn': 'Tswana', 'tum': 'Tumbuka', 'tr': 'Turkish', 'tk': 'Turkmen', 'uk': 'Ukrainian', 
    'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek', 've': 'Venda', 'vi': 'Vietnamese', 
    'war': 'Waray', 'cy': 'Welsh', 'fy': 'Western Frisian', 'wo': 'Wolof', 'xh': 'Xhosa', 
    'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}
# ------------------ Session State Setup ------------------ #
def init_session_state():
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'results_count' not in st.session_state:
        st.session_state.results_count = 5
    if 'transcripts' not in st.session_state:
        st.session_state.transcripts = {}
    if 'notes' not in st.session_state:
        st.session_state.notes = {}
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    if 'selected_languages' not in st.session_state:
        st.session_state.selected_languages = ['en']

# ------------------ Functions ------------------ #
def search_youtube_videos(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            videos = []
            for entry in search_results['entries']:
                thumbnail_url = f"https://img.youtube.com/vi/{entry['id']}/maxresdefault.jpg"
                try:
                    response = requests.head(thumbnail_url)
                    if response.status_code != 200:
                        thumbnail_url = f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg"
                except:
                    thumbnail_url = f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg"
                
                videos.append({
                    'id': entry['id'],
                    'title': entry['title'],
                    'url': f"https://www.youtube.com/watch?v={entry['id']}",
                    'thumbnail': thumbnail_url,
                    'channel': entry.get('uploader', 'Unknown channel'),
                    'duration': entry.get('duration', 'N/A')
                })
            return videos
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

def get_available_languages(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_langs = []
        
        for transcript in transcript_list:
            if transcript.is_generated:
                lang_type = "Auto-generated"
            else:
                lang_type = "Manual"
            
            available_langs.append({
                'code': transcript.language_code,
                'name': transcript.language,
                'type': lang_type,
                'translatable': transcript.is_translatable
            })
            
            if transcript.is_translatable:
                for translation_lang in transcript.translation_languages:
                    available_langs.append({
                        'code': translation_lang['language_code'],
                        'name': translation_lang['language'],
                        'type': f"Translation ({lang_type})",
                        'translatable': False
                    })
        
        return available_langs
    except Exception as e:
        st.error(f"Error getting available languages: {str(e)}")
        return []

def language_selector(video_id):
    available_langs = get_available_languages(video_id)
    if not available_langs:
        return []
    
    lang_options = []
    for lang in available_langs:
        display_name = f"{lang['name']} ({lang['code']}) - {lang['type']}"
        lang_options.append((lang['code'], display_name))
    
    selected = st.multiselect(
        "Select transcript language(s):",
        options=[opt[1] for opt in lang_options],
        default=[opt[1] for opt in lang_options if opt[0] in st.session_state.selected_languages],
        key=f"lang_select_{video_id}"
    )
    
    selected_codes = []
    for sel in selected:
        for code, name in lang_options:
            if name == sel:
                selected_codes.append(code)
                break
    
    st.session_state.selected_languages = selected_codes
    return selected_codes

def fetch_transcript(video_id, language_codes=['en']):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=language_codes)
        return "\n".join([seg['text'] for seg in transcript]), None
    except NoTranscriptFound:
        available_langs = get_available_languages(video_id)
        return None, available_langs
    except Exception as e:
        return None, str(e)

def translate_text(text, target_language='en'):
    try:
        prompt = f"""
        Translate the following text to {LANGUAGE_MAP.get(target_language, target_language)}.
        Preserve all formatting, special terms, and technical jargon.
        
        Text to translate:
        {text}
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def generate_notes(transcript, language='en'):
    try:
        prompt = f"""
        Create comprehensive study notes from this YouTube video transcript.
        The transcript is in {LANGUAGE_MAP.get(language, language)}.
        
        Include:
        1. Key Concepts (bullet points)
        2. Important Definitions
        3. Practical Examples
        4. Summary (3-5 sentences)
        
        Format the output in Markdown with proper headings.
        
        Transcript:
        {transcript}
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating notes: {str(e)}"

# ------------------ UI Components ------------------ #
def video_card(video):
    with st.container():
        st.markdown(f'<div class="video-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2], gap="medium")
        
        with col1:
            try:
                response = requests.get(video['thumbnail'])
                img = Image.open(io.BytesIO(response.content))
                st.image(img, use_container_width=True)
            except:
                st.image("https://via.placeholder.com/320x180?text=No+Thumbnail", 
                        use_container_width=True)
        
        with col2:
            st.markdown(f"### [{video['title']}]({video['url']})")
            st.caption(f"🎬 {video['channel']} • ⏱️ {video['duration']} sec")
            
            selected_langs = language_selector(video['id'])
            
            tab1, tab2 = st.tabs(["📜 Transcript", "📝 Study Notes"])
            
            with tab1:
                if st.button("Get Transcript", key=f"trans_btn_{video['id']}"):
                    with st.spinner("Fetching transcript..."):
                        transcript, error = fetch_transcript(video['id'], selected_langs)
                        if transcript:
                            st.session_state.transcripts[video['id']] = transcript
                            st.session_state.notes.pop(video['id'], None)
                            st.rerun()
                        elif error and isinstance(error, list):
                            st.error(f"No transcript available in selected languages. Available languages: {', '.join([lang['name'] for lang in error])}")
                        else:
                            st.error(f"Error fetching transcript: {error}")
                
                if video['id'] in st.session_state.transcripts:
                    st.markdown(st.session_state.transcripts[video['id']])
            
            with tab2:
                if video['id'] in st.session_state.transcripts:
                    if st.button("Generate Notes", key=f"notes_btn_{video['id']}"):
                        with st.spinner("Generating AI-powered notes..."):
                            try:
                                lang = detect(st.session_state.transcripts[video['id']][:500])
                            except:
                                lang = 'en'
                            
                            notes = generate_notes(
                                st.session_state.transcripts[video['id']],
                                language=lang
                            )
                            st.session_state.notes[video['id']] = notes
                            st.rerun()
                
                    if video['id'] in st.session_state.notes:
                        st.markdown(st.session_state.notes[video['id']])
                else:
                    st.info("First fetch the transcript to generate notes")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------ Main App ------------------ #
def main():
    init_session_state()
    
    st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #4a90e2;
        background-color: #4a90e2;
        color: white;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #3a7bc8;
        border-color: #3a7bc8;
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 0.75rem;
        border: 1px solid #ddd;
    }
    .video-card {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🌍 Multi-Language YouTube Study Notes")
    st.markdown("""
    <div style="text-align:center; margin-bottom:2rem;">
        <p style="color:#666; font-size:1.1rem;">
        Convert YouTube videos in any language to structured study materials
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(key='search_form'):
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input("", 
                                placeholder="Search for videos in any language...", 
                                label_visibility="collapsed",
                                value=st.session_state.last_query)
        with col2:
            submit_button = st.form_submit_button("🔍 Search")
    
    if submit_button and query:
        st.session_state.last_query = query
        with st.spinner(f"Searching for '{query}'..."):
            st.session_state.search_results = search_youtube_videos(query, max_results=st.session_state.results_count)
            st.rerun()
    
    if st.session_state.search_results:
        st.subheader("🎥 Search Results")
        st.markdown("---")
        
        for video in st.session_state.search_results:
            video_card(video)
            st.markdown("---")
        
        if st.button("Load More Results", use_container_width=True):
            st.session_state.results_count += 5
            with st.spinner("Loading more results..."):
                st.session_state.search_results = search_youtube_videos(
                    st.session_state.last_query, 
                    max_results=st.session_state.results_count
                )
            st.rerun()

if __name__ == "__main__":
    main()