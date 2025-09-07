import streamlit as st
import asyncio
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Import existing modules
from models import MangaRequest, CharacterRequest, ChapterRequest, PanelRequest, MainRequest
from services import generate_chapters, generate_characters, process_chapter, process_panel
from utils import clean_string, get_pdf, generate_image
from prompts import character_prompt
from gemini import client

# Page configuration
st.set_page_config(
    page_title="NanoBanana Manga Generator",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
    .info-box {
        background-color: #222831;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4ecdc4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Persistence configuration
STATE_FILE = "nanobanana_state.json"
DATA_DIR = Path("nanobanana_data")

def ensure_data_dir():
    """Ensure data directory exists"""
    DATA_DIR.mkdir(exist_ok=True)

def save_state_to_file():
    """Save session state to JSON file"""
    try:
        ensure_data_dir()
        state_file_path = DATA_DIR / STATE_FILE
        
        # Prepare state for serialization
        state_to_save = {
            'manga_history': [],
            'generation_progress': st.session_state.get('generation_progress', 0),
            'current_step': st.session_state.get('current_step', ""),
            'generated_images': st.session_state.get('generated_images', []),
            'generated_pdf': st.session_state.get('generated_pdf'),
            'manga_data': None,  # Will be handled separately
            'current_carousel_index': st.session_state.get('current_carousel_index', 0),
            'show_carousel': st.session_state.get('show_carousel', False),
            'show_pdf': st.session_state.get('show_pdf'),
            'carousel_panel_index': st.session_state.get('carousel_panel_index', 0),
            'last_saved': datetime.now().isoformat()
        }
        
        # Handle manga history with serializable data
        if 'manga_history' in st.session_state:
            for manga in st.session_state.manga_history:
                manga_entry = {
                    'title': manga['title'],
                    'chapters': manga['chapters'],
                    'panels': manga['panels'],
                    'images': manga['images'],
                    'pdf': manga['pdf'],
                    'timestamp': manga['timestamp'],
                    'manga_data': None  # Will be reconstructed from other data
                }
                
                # Save manga data separately if it exists
                if manga.get('manga_data'):
                    manga_data = manga['manga_data']
                    manga_entry['manga_data'] = {
                        'title': manga_data.title,
                        'global_style': {
                            'art_style_description': manga_data.global_style.art_style_description,
                            'character_sheets': [
                                {
                                    'character_id': char.character_id,
                                    'personality': char.personality,
                                    'detailed_appearence': char.detailed_appearence
                                }
                                for char in manga_data.global_style.character_sheets
                            ]
                        },
                        'chapters': [
                            {
                                'chapter_number': ch.chapter_number,
                                'chapter_title': ch.chapter_title,
                                'story': ch.story
                            }
                            for ch in manga_data.chapters
                        ]
                    }
                
                state_to_save['manga_history'].append(manga_entry)
        
        # Save to file
        with open(state_file_path, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        st.error(f"Error saving state: {e}")

def load_state_from_file():
    """Load session state from JSON file"""
    try:
        ensure_data_dir()
        state_file_path = DATA_DIR / STATE_FILE
        
        if not state_file_path.exists():
            return False
            
        with open(state_file_path, 'r', encoding='utf-8') as f:
            saved_state = json.load(f)
        
        # Restore session state
        st.session_state.generation_progress = saved_state.get('generation_progress', 0)
        st.session_state.current_step = saved_state.get('current_step', "")
        st.session_state.generated_images = saved_state.get('generated_images', [])
        st.session_state.generated_pdf = saved_state.get('generated_pdf')
        st.session_state.current_carousel_index = saved_state.get('current_carousel_index', 0)
        st.session_state.show_carousel = saved_state.get('show_carousel', False)
        st.session_state.show_pdf = saved_state.get('show_pdf')
        st.session_state.carousel_panel_index = saved_state.get('carousel_panel_index', 0)
        
        # Restore manga history
        st.session_state.manga_history = []
        for manga_entry in saved_state.get('manga_history', []):
            # Reconstruct manga data if available
            manga_data = None
            if manga_entry.get('manga_data'):
                try:
                    from models import Manga, GlobalStyle, CharacterSheet, Chapter
                    
                    # Reconstruct character sheets
                    character_sheets = [
                        CharacterSheet(
                            character_id=char['character_id'],
                            personality=char['personality'],
                            detailed_appearence=char['detailed_appearence']
                        )
                        for char in manga_entry['manga_data']['global_style']['character_sheets']
                    ]
                    
                    # Reconstruct global style
                    global_style = GlobalStyle(
                        art_style_description=manga_entry['manga_data']['global_style']['art_style_description'],
                        character_sheets=character_sheets
                    )
                    
                    # Reconstruct chapters
                    chapters = [
                        Chapter(
                            chapter_number=ch['chapter_number'],
                            chapter_title=ch['chapter_title'],
                            story=ch['story']
                        )
                        for ch in manga_entry['manga_data']['chapters']
                    ]
                    
                    # Reconstruct manga
                    manga_data = Manga(
                        title=manga_entry['manga_data']['title'],
                        global_style=global_style,
                        chapters=chapters
                    )
                except Exception as e:
                    st.warning(f"Could not reconstruct manga data for {manga_entry['title']}: {e}")
            
            # Create manga entry
            manga = {
                'title': manga_entry['title'],
                'chapters': manga_entry['chapters'],
                'panels': manga_entry['panels'],
                'images': manga_entry['images'],
                'pdf': manga_entry['pdf'],
                'manga_data': manga_data,
                'timestamp': manga_entry['timestamp']
            }
            st.session_state.manga_history.append(manga)
        
        return True
        
    except Exception as e:
        st.error(f"Error loading state: {e}")
        return False

def clear_persisted_state():
    """Clear persisted state file"""
    try:
        ensure_data_dir()
        state_file_path = DATA_DIR / STATE_FILE
        if state_file_path.exists():
            state_file_path.unlink()
    except Exception as e:
        st.error(f"Error clearing state: {e}")

# Initialize session state
if 'state_loaded' not in st.session_state:
    # Try to load state from file
    if load_state_from_file():
        st.session_state.state_loaded = True
        st.success("📁 Previous session restored!")
    else:
        # Initialize with default values
        st.session_state.generation_progress = 0
        st.session_state.current_step = ""
        st.session_state.generated_images = []
        st.session_state.generated_pdf = None
        st.session_state.manga_data = None
        st.session_state.manga_history = []
        st.session_state.current_carousel_index = 0
        st.session_state.show_carousel = False
        st.session_state.show_pdf = None
        st.session_state.carousel_panel_index = 0
        st.session_state.state_loaded = True

# Ensure all required session state attributes exist
required_attrs = [
    'generation_progress', 'current_step', 'generated_images', 'generated_pdf',
    'manga_data', 'manga_history', 'current_carousel_index', 'show_carousel',
    'show_pdf', 'carousel_panel_index', 'state_loaded'
]

for attr in required_attrs:
    if attr not in st.session_state:
        if attr == 'generation_progress':
            st.session_state[attr] = 0
        elif attr in ['current_step', 'generated_pdf', 'manga_data', 'show_pdf']:
            st.session_state[attr] = None
        elif attr in ['generated_images', 'manga_history']:
            st.session_state[attr] = []
        elif attr in ['current_carousel_index', 'carousel_panel_index']:
            st.session_state[attr] = 0
        elif attr in ['show_carousel', 'state_loaded']:
            st.session_state[attr] = False

def check_api_key():
    """Check if API key is configured"""
    try:
        # Try to access the client to see if API key is working
        if hasattr(client, 'models'):
            return True
    except:
        pass
    return False

def safe_get_session_state(key, default=None):
    """Safely get session state value with default"""
    try:
        return st.session_state.get(key, default)
    except AttributeError:
        return default

def main_page():
    """Main manga generation page"""
    st.markdown('<h1 class="main-header">🍌 NanoBanana Manga Generator</h1>', unsafe_allow_html=True)
    
    # Check API key
    if not check_api_key():
        st.error("⚠️ API Key not configured. Please go to Configuration page to set up your Gemini API key.")
        return
    
    st.markdown('<div class="info-box">Create your own manga with AI! Enter your story idea below and let NanoBanana generate chapters, characters, and panels for you.</div>', unsafe_allow_html=True)
    
    # Input form
    with st.form("manga_generation_form"):
        st.markdown('<div class="section-header">📝 Story Input</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            prompt = st.text_area(
                "Main Story Prompt",
                placeholder="Enter your manga story idea here...\n\nExample: A young ninja discovers they have the power to control shadows and must learn to use this ability to protect their village from an ancient evil.",
                height=150,
                help="Describe the main concept, characters, and world of your manga"
            )
            
            context = st.text_area(
                "Additional Context",
                placeholder="Any additional world-building, character backgrounds, or story elements...",
                height=100,
                help="Provide additional context about your story world"
            )
        
        with col2:
            instructions = st.text_area(
                "Special Instructions",
                placeholder="Any specific requirements for art style, pacing, or story elements...",
                height=100,
                help="Special instructions for generation"
            )
            
            num_chapters = st.slider(
                "Number of Chapters",
                min_value=1,
                max_value=10,
                value=3,
                help="How many chapters to generate"
            )
            
            lang = st.selectbox(
                "Language for Dialogues",
                options=["english", "spanish", "french", "german", "japanese", "korean", "chinese"],
                index=0,
                help="Language for character dialogues (other elements remain in English)"
            )
        
        # Advanced options
        with st.expander("🎨 Advanced Options"):
            col3, col4 = st.columns(2)
            
            with col3:
                art_style = st.text_input(
                    "Art Style Description",
                    value="Modern manga style with clean lines and dynamic action sequences",
                    help="Describe the visual style you want",
                )
            
            with col4:
                model_choice = st.selectbox(
                    "AI Model",
                    options=["gemini-2.5-pro", "gemini-2.5-flash"],
                    index=0,
                    help="Choose the AI model for generation",
                )
        
        submitted = st.form_submit_button("🚀 Generate Manga", type="primary")
    
    if submitted:
        if not prompt.strip():
            st.error("Please enter a story prompt!")
            return
        
        # Create request object
        request = MainRequest(
            prompt=f"{prompt}\n\n{art_style if art_style else ''}",
            context=context,
            instructions=instructions,
            num_chapters=num_chapters,
            lang=lang,
            model=model_choice
        )
        
        # Start generation process
        asyncio.run(generate_manga_async(request))

async def generate_manga_async(request: MainRequest):
    """Async function to handle manga generation with progress tracking"""
    try:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create containers for real-time updates
        manga_info_container = st.container()
        character_container = st.container()
        chapter_container = st.container()
        
        # Step 1: Generate chapters
        status_text.text("📚 Generating manga structure and chapters...")
        progress_bar.progress(10)
        
        manga_request = MangaRequest(
            prompt=request.prompt,
            context=request.context,
            instructions=request.instructions,
            num_chapters=request.num_chapters,
            lang=request.lang,
            model=request.model
        )
        
        manga = await generate_chapters(manga_request)
        st.session_state.manga_data = manga
        os.makedirs(f"nanobanana_data/{manga.title}", exist_ok=True)
        
        # Display manga details immediately
        with manga_info_container:
            st.markdown('<div class="section-header">📖 Generated Manga Details</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📚 Manga Information")
                st.write(f"**Title:** {manga.title}")
                st.write(f"**Chapters:** {len(manga.chapters)}")
                st.write(f"**Art Style:** {manga.global_style.art_style_description}")
            
            with col2:
                st.subheader("📝 Chapter Overview")
                for i, chapter in enumerate(manga.chapters):
                    with st.expander(f"Chapter {i+1}: {chapter.chapter_title}", expanded=False):
                        st.write(chapter.story)
        
        progress_bar.progress(30)
        status_text.text("🎭 Generating character designs...")
        
        # Step 2: Generate characters with real-time display
        with character_container:
            st.markdown('<div class="section-header">🎭 Character Generation</div>', unsafe_allow_html=True)
            character_cols = st.columns(min(len(manga.global_style.character_sheets), 3))
            
            for idx, character in enumerate(manga.global_style.character_sheets):
                with character_cols[idx % 3]:
                    st.markdown(f"**{character.character_id}**")
                    st.write(f"*{character.personality}*")
                    st.write(character.detailed_appearence)
                    # Placeholder for character image
                    character_image_placeholder = st.empty()
                    character_image_placeholder.info("🔄 Generating character image...")
        
        # Generate character images one by one with real-time updates
        for idx, character in enumerate(manga.global_style.character_sheets):
            cprompt = character_prompt.format(**{
                'character_id': character.character_id,
                'personality': character.personality,
                'detailed_appearance': character.detailed_appearence,
                'art_style_description': manga.global_style.art_style_description
            })
            path = f'nanobanana_data/{await clean_string(manga.title)}/{await clean_string(character.character_id)}.png'
            path = await generate_image(cprompt, path, [])
            
            # Update the character image in real-time
            with character_cols[idx % 3]:
                if os.path.exists(path):
                    character_image_placeholder = st.empty()
                    character_image_placeholder.image(path, caption=f"{character.character_id}")
                else:
                    st.error(f"Failed to generate image for {character.character_id}")
        
        progress_bar.progress(50)
        
        # Step 3: Process chapters and panels
        with chapter_container:
            st.markdown('<div class="section-header">📖 Chapter Processing & Panel Generation</div>', unsafe_allow_html=True)
            panel_gallery_container = st.container()
        
        all_images = []
        current_panel = 0   
        total_panels = 0
        
        for chapter_idx, chapter in enumerate(manga.chapters):
            status_text.text(f"📖 Processing Chapter {chapter_idx + 1}: {chapter.chapter_title}")
            
            chapter_script = await process_chapter(ChapterRequest(
                chapter=chapter,
                global_style=manga.global_style,
                lang=request.lang,
                model=request.model
            ))
            total_panels = sum(len(page.panels) for page in chapter_script.pages)
            
            # Display chapter processing info
            with chapter_container:
                st.info(f"📖 Processing Chapter {chapter_idx + 1}: {chapter.chapter_title} ({total_panels} panels)")
            
            for page_idx, page in enumerate(chapter_script.pages):
                for panel in page.panels:
                    status_text.text(f"🎨 Generating panel {current_panel + 1}/{total_panels}")
                    
                    imgpath = await process_panel(PanelRequest(
                        manga=manga.title,
                        scene_description=panel.scene_description,
                        global_style=manga.global_style,
                        id=f"{chapter_idx}_{page_idx}_{panel.panel_number}",
                        model=request.model
                    ))
                    
                    all_images.append(imgpath)
                    current_panel += 1
                    
                    # Update progress
                    progress = min(50 + (current_panel / total_panels) * 40, 100)
                    progress_bar.progress(int(progress))
                    
                    # Show generated panel in real-time
                    with panel_gallery_container:
                        if os.path.exists(imgpath):
                            cols = st.columns(3)
                            with cols[current_panel % 3]:
                                st.image(imgpath, caption=f"Panel {current_panel} - Ch{chapter_idx + 1}P{page_idx + 1}")
                        else:
                            st.warning(f"Panel {current_panel} generation failed")
        
        # Step 4: Create PDF
        status_text.text("📄 Creating PDF...")
        progress_bar.progress(90)
        
        if all_images:
            pdf_path = await get_pdf(all_images, f"nanobanana_data/{await clean_string(manga.title)}/generated_manga.pdf")
            st.session_state.generated_pdf = pdf_path
        
        progress_bar.progress(100)
        status_text.text("✅ Generation complete!")
        
        # Store results
        st.session_state.generated_images = all_images
        
        # Save to manga history
        import time
        manga_entry = {
            'title': manga.title,
            'chapters': len(manga.chapters),
            'panels': len(all_images),
            'images': all_images,
            'pdf': st.session_state.generated_pdf,
            'manga_data': manga,
            'timestamp': time.time()
        }
        st.session_state.manga_history.append(manga_entry)
        
        # Auto-save state
        save_state_to_file()
        
        # Show success message
        st.markdown('<div class="success-box">🎉 Your manga has been generated successfully!</div>', unsafe_allow_html=True)
        
        # Clear the status text and progress bar
        status_text.empty()
        progress_bar.empty()
        
        # Display final results summary
        with st.container():
            st.markdown('<div class="section-header">�� Generation Summary</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Chapters Generated", len(manga.chapters))
            with col2:
                st.metric("Panels Created", len(all_images))
            with col3:
                st.metric("Characters Designed", len(manga.global_style.character_sheets))
        
        # Display results
        display_results()
        
    except Exception as e:
        st.error(f"❌ Error during generation: {str(e)}")
        st.exception(e)

def display_results():
    """Display generated manga results"""
    st.markdown('<div class="section-header">📚 Generated Manga</div>', unsafe_allow_html=True)
    
    manga_data = safe_get_session_state('manga_data')
    if manga_data:
        manga = manga_data
        
        # Display manga info
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📖 Manga Information")
            st.write(f"**Title:** {manga.title}")
            st.write(f"**Chapters:** {len(manga.chapters)}")
            st.write(f"**Art Style:** {manga.global_style.art_style_description}")
        
        with col2:
            st.subheader("🎭 Characters")
            for character in manga.global_style.character_sheets:
                st.write(f"**{character.character_id}:** {character.personality}")
        
        # Display chapters
        st.subheader("📚 Chapter Overview")
        for i, chapter in enumerate(manga.chapters):
            with st.expander(f"Chapter {i+1}: {chapter.chapter_title}"):
                st.write(chapter.story)
    
    # Display images
    if st.session_state.generated_images:
        st.markdown('<div class="section-header">🖼️ Generated Panels</div>', unsafe_allow_html=True)
        
        # Create image gallery
        cols = st.columns(3)
        for idx, img_path in enumerate(st.session_state.generated_images):
            if os.path.exists(img_path):
                with cols[idx % 3]:
                    st.image(img_path, caption=f"Panel {idx + 1}")
                    
                    # Download button for individual image
                    with open(img_path, "rb") as file:
                        st.download_button(
                            label=f"📥 Download Panel {idx + 1}",
                            data=file.read(),
                            file_name=f"panel_{idx + 1}.png",
                            mime="image/png"
                        )
    
    # PDF download
    if st.session_state.generated_pdf and os.path.exists(st.session_state.generated_pdf):
        st.markdown('<div class="section-header">📄 Download Complete Manga</div>', unsafe_allow_html=True)
        
        with open(st.session_state.generated_pdf, "rb") as file:
            # Extract filename from path
            pdf_filename = os.path.basename(st.session_state.generated_pdf)
            st.download_button(
                label="📥 Download Complete Manga PDF",
                data=file.read(),
                file_name=pdf_filename,
                mime="application/pdf",
                type="primary"
            )

def config_page():
    """Configuration page for API keys and settings"""
    st.markdown('<h1 class="main-header">⚙️ Configuration</h1>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">Configure your API keys and settings here. Your API key is stored securely in your session.</div>', unsafe_allow_html=True)
    
    # API Key configuration
    st.subheader("🔑 Gemini API Key")
    
    current_key = st.text_input(
        "Enter your Gemini API Key",
        type="password",
        help="Get your API key from https://makersuite.google.com/app/apikey",
        placeholder="Enter your API key here..."
    )
    
    if st.button("💾 Save API Key"):
        if current_key:
            # Update the client with new API key
            try:
                from google import genai
                global client
                client = genai.Client(api_key=current_key)
                st.success("✅ API key saved successfully!")
            except Exception as e:
                st.error(f"❌ Error saving API key: {str(e)}")
        else:
            st.error("Please enter a valid API key!")
    
    # Manual state management
    st.markdown("---")
    st.subheader("🗂️ State Management")
    
    col_state1, col_state2 = st.columns(2)
    
    with col_state1:
        if st.button("📁 Load Previous Session"):
            if load_state_from_file():
                st.success("✅ Previous session loaded!")
                st.rerun()
            else:
                st.error("❌ No previous session found!")
    
    with col_state2:
        if st.button("🗑️ Clear All Data"):
            clear_persisted_state()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ All data cleared!")
            st.rerun()

def gallery_page():
    """Gallery page to view generated content"""
    st.markdown('<h1 class="main-header">🖼️ Manga Gallery</h1>', unsafe_allow_html=True)
    
    manga_history = safe_get_session_state('manga_history', [])
    if not manga_history:
        st.info("📚 No mangas generated yet. Go to the main page to create your first manga!")
        return
    
    st.markdown('<div class="info-box">Browse and view all your generated mangas. Click "View" to see panels in a carousel or "View PDF" to open the complete manga.</div>', unsafe_allow_html=True)
    
    # Display manga list
    st.subheader("📚 Your Generated Mangas")
    
    for idx, manga in enumerate(manga_history):
        with st.container():
            st.markdown("---")
            
            # Manga info row
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"### 📖 {manga['title']}")
                st.write(f"**Chapters:** {manga['chapters']} | **Panels:** {manga['panels']}")
                if manga['manga_data']:
                    st.write(f"**Style:** {manga['manga_data'].global_style.art_style_description}")
            
            with col2:
                if st.button(f"👁️ View", key=f"view_{idx}"):
                    st.session_state.current_carousel_index = idx
                    st.session_state.show_carousel = True
            
            with col3:
                if manga['pdf'] and os.path.exists(manga['pdf']):
                    if st.button(f"📄 PDF", key=f"pdf_{idx}"):
                        st.session_state.show_pdf = manga['pdf']
                else:
                    st.button(f"📄 PDF", key=f"pdf_{idx}", disabled=True)
            
            with col4:
                if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                    st.session_state.manga_history.pop(idx)
                    save_state_to_file()  # Auto-save after deletion
                    st.rerun()
    
    # Carousel view
    if safe_get_session_state('show_carousel', False):
        show_carousel()
    
    # PDF view
    show_pdf = safe_get_session_state('show_pdf')
    if show_pdf:
        show_pdf_viewer(show_pdf)

def show_carousel():
    """Show carousel for selected manga"""
    manga_idx = safe_get_session_state('current_carousel_index', 0)
    manga_history = safe_get_session_state('manga_history', [])
    if manga_idx >= len(manga_history):
        st.error("Invalid manga index!")
        return
    manga = manga_history[manga_idx]
    
    st.markdown("---")
    st.markdown(f"### 🎠 Carousel: {manga['title']}")
    
    # Carousel controls
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ First"):
            st.session_state.carousel_panel_index = 0
            st.rerun()
    
    with col2:
        if st.button("⏭️ Last"):
            st.session_state.carousel_panel_index = len(manga['images']) - 1
            st.rerun()
    
    with col3:
        if st.button("❌ Close"):
            st.session_state.show_carousel = False
            st.rerun()
    
    with col4:
        if st.button("📄 View PDF"):
            st.session_state.show_pdf = manga['pdf']
            st.rerun()
    
    # Initialize panel index if not set
    current_panel = safe_get_session_state('carousel_panel_index', 0)
    
    # Panel navigation
    if manga['images']:
        total_panels = len(manga['images'])
        
        # Ensure index is within bounds
        if current_panel >= total_panels:
            current_panel = total_panels - 1
            st.session_state.carousel_panel_index = current_panel
        elif current_panel < 0:
            current_panel = 0
            st.session_state.carousel_panel_index = current_panel
        
        # Display current panel
        img_path = manga['images'][current_panel]
        if os.path.exists(img_path):
            st.image(img_path, caption=f"Panel {current_panel + 1} of {total_panels}")
            
            # Panel navigation buttons
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 1, 1, 1])
            
            with nav_col1:
                if st.button("⬅️ Previous"):
                    if current_panel > 0:
                        st.session_state.carousel_panel_index = current_panel - 1
                        save_state_to_file()  # Auto-save navigation state
                        st.rerun()
            
            with nav_col2:
                if st.button("➡️ Next"):
                    if current_panel < total_panels - 1:
                        st.session_state.carousel_panel_index = current_panel + 1
                        save_state_to_file()  # Auto-save navigation state
                        st.rerun()
            
            with nav_col3:
                # Panel selector
                selected_panel = st.selectbox(
                    "Jump to Panel",
                    range(1, total_panels + 1),
                    index=current_panel,
                    key="panel_selector"
                )
                if selected_panel != current_panel + 1:
                    st.session_state.carousel_panel_index = selected_panel - 1
                    save_state_to_file()  # Auto-save navigation state
                    st.rerun()
            
            with nav_col4:
                # Download current panel
                with open(img_path, "rb") as file:
                    st.download_button(
                        label="📥 Download",
                        data=file.read(),
                        file_name=f"{manga['title']}_panel_{current_panel + 1}.png",
                        mime="image/png",
                        key=f"download_panel_{current_panel}"
                    )
        else:
            st.error(f"Image not found: {img_path}")

def show_pdf_viewer(pdf_path):
    """Show PDF viewer for selected manga"""
    st.markdown("---")
    st.markdown("### 📄 PDF Viewer")
    
    if pdf_path and os.path.exists(pdf_path):
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("❌ Close PDF"):
                st.session_state.show_pdf = None
                st.rerun()
            
            # PDF download
            with open(pdf_path, "rb") as file:
                st.download_button(
                    label="📥 Download PDF",
                    data=file.read(),
                    file_name="generated_manga.pdf",
                    mime="application/pdf",
                    key="download_pdf"
                )
        
        with col2:
            # Display PDF using iframe (if supported by browser)
            try:
                with open(pdf_path, "rb") as file:
                    pdf_bytes = file.read()
                    st.download_button(
                        label="📄 Open PDF in New Tab",
                        data=pdf_bytes,
                        file_name="manga.pdf",
                        mime="application/pdf",
                        key="open_pdf"
                    )
                
                # Alternative: Show PDF info
                st.info("💡 Click the download button above to view the PDF. For best experience, open it in a new tab.")
                
            except Exception as e:
                st.error(f"Error loading PDF: {e}")
    else:
        st.error("PDF file not found or not generated yet.")

def about_page():
    """About page with project information"""
    st.markdown('<h1 class="main-header">ℹ️ About NanoBanana</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h3>🍌 What is NanoBanana?</h3>
    <p>NanoBanana is an AI-powered manga generation tool that creates complete manga stories, characters, and panels from simple text prompts. Using Google's Gemini AI, it generates structured manga content including:</p>
    <ul>
        <li>📚 Complete chapter outlines and story structure</li>
        <li>🎭 Detailed character designs and personalities</li>
        <li>🎨 Individual manga panels with scene descriptions</li>
        <li>📄 Complete PDF compilation</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🚀 Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **✨ Core Features:**
        - AI-powered story generation
        - Character design automation
        - Panel-by-panel manga creation
        - Multiple language support
        - PDF export functionality
        - Interactive web interface
        """)
    
    with col2:
        st.markdown("""
        **🎨 Customization:**
        - Art style specification
        - Chapter count control
        - Character personality design
        - Scene composition control
        - Advanced generation options
        """)
    
    st.subheader("🔧 Technical Details")
    st.markdown("""
    - **AI Model:** Google Gemini 2.5 Pro/Flash
    - **Image Generation:** Gemini 2.5 Flash Image Preview
    - **Framework:** Streamlit for web interface
    - **Data Models:** Pydantic for structured data
    - **PDF Generation:** img2pdf library
    - **Image Processing:** Pillow (PIL)
    """)
    
    st.subheader("📝 How to Use")
    st.markdown("""
    1. **Configure:** Set up your Gemini API key in the Configuration page
    2. **Create:** Enter your story idea in the main page
    3. **Customize:** Adjust settings like chapter count and art style
    4. **Generate:** Click the generate button and wait for completion
    5. **Download:** View and download your generated manga
    """)

# Main app
def main():
    """Main app function with navigation"""
    
    # Sidebar navigation
    st.sidebar.title("🍌 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🏠 Home", "⚙️ Configuration", "🖼️ Gallery", "ℹ️ About"]
    )
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Session Info")
    
    manga_data = safe_get_session_state('manga_data')
    if manga_data:
        st.sidebar.write(f"**Current Manga:** {manga_data.title}")
        st.sidebar.write(f"**Chapters:** {len(manga_data.chapters)}")
    
    generated_images = safe_get_session_state('generated_images', [])
    if generated_images:
        st.sidebar.write(f"**Generated Panels:** {len(generated_images)}")
    
    manga_history = safe_get_session_state('manga_history', [])
    if manga_history:
        st.sidebar.write(f"**Total Mangas:** {len(manga_history)}")
        total_panels = sum(manga['panels'] for manga in manga_history)
        st.sidebar.write(f"**Total Panels:** {total_panels}")
    
    # Show last saved time if available
    state_file_path = DATA_DIR / STATE_FILE
    if state_file_path.exists():
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
            last_saved = saved_state.get('last_saved')
            if last_saved:
                last_saved_dt = datetime.fromisoformat(last_saved)
                st.sidebar.write(f"**Last Saved:** {last_saved_dt.strftime('%H:%M:%S')}")
        except:
            pass
    
    # Clear session button
    if st.sidebar.button("🗑️ Clear Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        clear_persisted_state()  # Also clear persisted state
        st.rerun()
    
    # Route to appropriate page
    if page == "🏠 Home":
        main_page()
    elif page == "⚙️ Configuration":
        config_page()
    elif page == "🖼️ Gallery":
        gallery_page()
    elif page == "ℹ️ About":
        about_page()

if __name__ == "__main__":
    main()
