import streamlit as st
import time
from pathlib import Path
import tempfile
import json
import shutil
from datetime import datetime
import base64
from PIL import Image

from ocr import process_pdf
from vision import analyze_paper_media
from processor import process_research_paper
from synthesis import create_synthesis

class SessionManager:
    def __init__(self):
        self.base_path = Path("sessions")
        self.base_path.mkdir(exist_ok=True)
        self.current_session = None

    def create_session(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_path = self.base_path / timestamp
        session_path.mkdir(exist_ok=True)
        self.current_session = session_path
        return session_path

    def get_path(self, filename):
        if not self.current_session:
            self.create_session()
        return self.current_session / filename

class FigureManager:
    def __init__(self, process_results_path: Path):
        self.process_results = self._load_process_results(process_results_path)
        
    def _load_process_results(self, path: Path) -> dict:
        """Load and parse process results JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading process results: {e}")
            return {}

    def get_essential_figures(self) -> list:
        """Get list of essential figures with their metadata."""
        try:
            media_analysis = self.process_results.get('paper_analysis', {}).get('media_analysis', [])
            return [
                {
                    'path': item['path'],
                    'type': item['type'],
                    'description': item.get('content', {}).get('description', ''),
                    'context': item.get('content', {}).get('reference_text', ''),
                    'analysis': item.get('analysis', {})
                }
                for item in media_analysis
                if item.get('analysis', {}).get('is_essential', False)
            ]
        except Exception as e:
            print(f"Error getting essential figures: {e}")
            return []

def display_synthesis_with_figures(synthesis_text: str, essential_figures: list):
    """Display synthesis with figures in appropriate positions."""
    # Split synthesis into sections
    sections = synthesis_text.split('\n\n')
    
    for section in sections:
        # Display section text
        st.markdown(section)
        
        # Check if any figures should be displayed here
        for figure in essential_figures:
            # Check if figure's path is mentioned in this section
            if figure['path'] in section:
                try:
                    # Create columns for figure and caption
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Display figure
                        image = Image.open(figure['path'])
                        st.image(image, caption=f"Figure: {Path(figure['path']).stem}")
                    
                    with col2:
                        # Display analysis
                        st.markdown("**Analysis**")
                        st.markdown(figure['analysis']['understanding_role'])
                        
                        if figure.get('context'):
                            with st.expander("Show Context"):
                                st.markdown(figure['context'])
                                
                except Exception as e:
                    st.error(f"Error displaying figure {figure['path']}: {str(e)}")

def process_paper_pipeline(pdf_file, session_manager):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            pdf_path = tmp_file.name

        # Step 1: OCR Processing
        st.write("### Step 1: OCR Processing")
        progress_bar = st.progress(0)
        
        ocr_output = process_pdf(pdf_path)
        if not ocr_output:
            st.error("OCR processing failed!")
            return False
            
        ocr_path = session_manager.get_path("ocr_results.json")
        with open(ocr_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_output, f, indent=2)
        progress_bar.progress(25)
        st.success("OCR processing complete!")

        # Step 2: Vision Analysis
        st.write("### Step 2: Vision Analysis")
        vision_output = analyze_paper_media(
            str(ocr_path),
            "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"
        )
        if not vision_output:
            st.error("Vision analysis failed!")
            return False
            
        vision_path = session_manager.get_path("vision_results.json")
        with open(vision_path, 'w', encoding='utf-8') as f:
            json.dump(vision_output, f, indent=2)
        progress_bar.progress(50)
        st.success("Vision analysis complete!")

        # Step 3: Processing
        st.write("### Step 3: Processing")
        process_output = process_research_paper(str(vision_path))
        if not process_output:
            st.error("Processing failed!")
            return False
            
        process_path = session_manager.get_path("process_results.json")
        with open(process_path, 'w', encoding='utf-8') as f:
            json.dump(process_output, f, indent=2)
        progress_bar.progress(75)
        st.success("Processing complete!")

        # Step 4: Synthesis
        st.write("### Step 4: Synthesis")
        synthesis_path = session_manager.get_path("synthesis.md")
        synthesis_output = create_synthesis(
            str(process_path),
            str(vision_path),
            str(synthesis_path)
        )
        if not synthesis_output:
            st.error("Synthesis failed!")
            return False
            
        progress_bar.progress(100)
        st.success("Synthesis complete!")

        # Clean up
        Path(pdf_path).unlink()
        
        return True

    except Exception as e:
        st.error(f"Error in pipeline: {str(e)}")
        return False

def main():
    st.set_page_config(
        page_title="Research Paper Analyzer",
        page_icon="📑",
        layout="wide"
    )

    st.title("Research Paper Analysis Pipeline")
    st.markdown("""
    Upload a research paper (PDF) to:
    1. Extract text and figures (OCR)
    2. Analyze visual content (Vision)
    3. Process and plan synthesis (Processing)
    4. Generate final synthesis (Synthesis)
    """)

    session_manager = SessionManager()
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        session_path = session_manager.create_session()
        st.info(f"Session created: {session_path}")

        if st.button("Start Analysis"):
            with st.spinner("Processing paper..."):
                success = process_paper_pipeline(uploaded_file, session_manager)
                
            if success:
                st.success("Analysis complete! Results saved in session folder.")
                
                # Initialize figure manager
                figure_manager = FigureManager(session_manager.get_path("process_results.json"))
                essential_figures = figure_manager.get_essential_figures()
                
                # Display results
                st.markdown("### Analysis Results")
                
                tabs = st.tabs(["Synthesis with Figures", "Generated Files", "Raw Results"])
                
                with tabs[0]:
                    synthesis_path = session_manager.get_path("synthesis.md")
                    if synthesis_path.exists():
                        with open(synthesis_path, 'r', encoding='utf-8') as f:
                            synthesis_text = f.read()
                        display_synthesis_with_figures(synthesis_text, essential_figures)
                
                with tabs[1]:
                    st.markdown("#### Generated Files:")
                    for file in session_manager.current_session.glob("*"):
                        st.write(f"- {file.name}")
                
                with tabs[2]:
                    st.markdown("#### Process Results:")
                    with open(session_manager.get_path("process_results.json"), 'r') as f:
                        st.json(json.load(f))

if __name__ == "__main__":
    main()