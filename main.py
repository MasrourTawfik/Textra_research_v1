import streamlit as st
import time
from pathlib import Path
import tempfile
import json
import shutil
from datetime import datetime
import base64
from PIL import Image
import re

from ocr import process_pdf
from vision import analyze_paper_media
from processor import process_research_paper
from synthesis import create_synthesis
from knowledge_graph import process_knowledge_graph


def display_knowledge_graph(graph_results, session_path=None):
    """Display knowledge graph results in Streamlit."""
    import matplotlib.pyplot as plt
    
    if not graph_results:
        st.error("No graph results to display")
        return

    # Display graph visualization first
    if graph_results.get('figure'):
        try:
            fig = graph_results['figure']
            plt.figure(fig.number)  # Activate the figure
            st.pyplot(fig, clear_figure=True)
        except Exception as e:
            st.error(f"Error displaying graph: {e}")
            # Try alternate display method
            if session_path:
                try:
                    st.image(f"{session_path}/knowledge_graph.png")
                except Exception as e2:
                    st.error(f"Error displaying saved graph image: {e2}")

    # Display entities
    if 'entities' in graph_results:
        st.success(f"Found {len(graph_results['entities'])} concepts")
        with st.expander("📋 View Extracted Concepts"):
            st.json(graph_results['entities'])
    
    # Display relationships
    if 'relationships' in graph_results and 'relationships' in graph_results['relationships']:
        st.success(f"Found {len(graph_results['relationships']['relationships'])} relationships")
        with st.expander("🔗 View Relationships"):
            st.json(graph_results['relationships'])
    
    # Add download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Concepts (JSON)",
            data=json.dumps(graph_results['entities'], indent=2),
            file_name="concepts.json",
            mime="application/json",
            key="download_concepts"
        )
    with col2:
        st.download_button(
            "📥 Download Relationships (JSON)",
            data=json.dumps(graph_results['relationships'], indent=2),
            file_name="relationships.json",
            mime="application/json",
            key="download_relationships"
        )
            
def process_and_display_graph(text: str, paper_title: str, session_path: str):
    """Process and display knowledge graph."""
    with st.spinner("Generating knowledge graph..."):
        graph_results = process_knowledge_graph(text, paper_title, session_path)
        if graph_results:
            display_knowledge_graph(graph_results, session_path)
        else:
            st.error("Could not generate knowledge graph")           
            
            
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
            essential_figures = []
            
            for item in media_analysis:
                if item.get('analysis', {}).get('is_essential', False):
                    # Extract figure number from path if possible
                    path = item['path']
                    figure_num = None
                    match = re.search(r'figure_(\d+)', path.lower())
                    if match:
                        figure_num = match.group(1)
                    
                    essential_figures.append({
                        'path': path,
                        'type': item['type'],
                        'number': figure_num,
                        'description': item.get('content', {}).get('description', ''),
                        'context': item.get('content', {}).get('reference_text', ''),
                        'analysis': item.get('analysis', {})
                    })
            
            return essential_figures
        except Exception as e:
            print(f"Error getting essential figures: {e}")
            return []

def display_synthesis_with_figures(synthesis_text: str, essential_figures: list):
    """Display synthesis with figures in appropriate positions."""
    # Compile regex patterns for figure references
    figure_patterns = [
        r'\*\*\(Reference:[^)]+\)\*\*',  # (Reference: arXiv:...)
        r'\[Insert Figure \d+ reference here[^]]*\]',  # [Insert Figure X reference here]
        r'Figure \d+',  # Simple Figure X reference
        r'Fig\. \d+',  # Fig. X reference
        r'\[Figure:[^\]]+\]',  # [Figure: Description]
        r'\(\[Figure:[^\]]+\]\)'  # ([Figure: Description])
    ]
    
    # Split synthesis into sections but preserve figure references
    sections = []
    current_section = []
    
    for line in synthesis_text.split('\n'):
        # Check if this line contains a figure reference
        has_figure_ref = any(re.search(pattern, line, re.IGNORECASE) for pattern in figure_patterns)
        
        if has_figure_ref:
            # Add accumulated section if it exists
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
            # Add figure reference as its own section
            sections.append(line)
        else:
            current_section.append(line)
    
    # Add final section if it exists
    if current_section:
        sections.append('\n'.join(current_section))

    # Display sections with figures
    for section in sections:
        # Check if this section is a figure reference
        is_figure_ref = any(re.search(pattern, section, re.IGNORECASE) for pattern in figure_patterns)
        
        if is_figure_ref:
            # Try to find corresponding figure
            for figure in essential_figures:
                # Extract figure number if present in the reference
                figure_num_match = re.search(r'Figure (\d+)|Fig\. (\d+)', section, re.IGNORECASE)
                found_figure = False
                
                if figure_num_match:
                    figure_num = figure_num_match.group(1) or figure_num_match.group(2)
                    if f"figure_{figure_num}" in figure['path'].lower():
                        found_figure = True
                else:
                    # Try to match by description
                    description_match = re.search(r'\[Figure:\s*([^\]]+)\]', section, re.IGNORECASE)
                    if description_match:
                        desc = description_match.group(1).strip().lower()
                        # Try to match by keywords in the description
                        if any(keyword in desc and keyword in figure['path'].lower() 
                              for keyword in ["architecture", "diagram", "flowchart", "model", "network"]):
                            found_figure = True
                
                if found_figure:
                    try:
                        # Create columns for figure and analysis
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Display figure
                            image = Image.open(figure['path'])
                            st.image(image, use_column_width=True)
                            
                        with col2:
                            # Display analysis
                            st.markdown("**Analysis**")
                            if figure.get('analysis', {}).get('understanding_role'):
                                st.markdown(figure['analysis']['understanding_role'])
                                
                            if figure.get('context'):
                                with st.expander("Show Context"):
                                    st.markdown(figure['context'])
                                    
                    except Exception as e:
                        print(f"Error displaying figure {figure['path']}: {e}")
                        continue
                        
        else:
            # Display regular section text
            st.markdown(section)





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
            "Your api key here"
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
    5. Generate knowledge graph (Graph Analysis)
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
                
                tabs = st.tabs(["Synthesis with Figures", "Generated Files", "Raw Results", "Knowledge Graph"])
                
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

                with tabs[3]:
                    st.markdown("#### Knowledge Graph Analysis")
                    with open(session_manager.get_path("vision_results.json"), 'r') as f:
                        vision_results = json.load(f)
                        text = " ".join(page.get("text", "") for page in vision_results.get("pages", []))
                        paper_title = vision_results.get("metadata", {}).get("title", "Research Paper")
                    
                    process_and_display_graph(text, paper_title, str(session_manager.current_session))
if __name__ == "__main__":
    main()