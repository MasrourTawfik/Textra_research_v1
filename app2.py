import streamlit as st
import json
from typing import Dict, List
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
import os
from openai import OpenAI
import PyPDF2
import re

# Set page config
st.set_page_config(
    page_title="RL Paper Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Force light theme and text contrast
st.markdown("""
    <style>
        /* Previous CSS rules remain... */

        /* JSON viewer specific styling */
        .stJson {
            background-color: white !important;
            color: black !important;
        }
        
        /* Style for the expander content */
        .streamlit-expanderContent {
            background-color: white !important;
            color: black !important;
        }
        
        /* JSON syntax highlighting colors */
        .json-formatter-row {
            background-color: white !important;
            color: black !important;
        }
        
        .streamlit-expanderContent pre {
            background-color: white !important;
            color: black !important;
        }
        
        /* Additional specific JSON styling */
        div[data-testid="stJson"] {
            background-color: white !important;
            color: black !important;
        }
        
        div[data-testid="stJson"] > pre {
            background-color: white !important;
            color: black !important;
        }
    </style>
""", unsafe_allow_html=True)
class RLPaperAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="ur api key here"
        )
        self.valid_types = {
            'theorem', 'equation', 'framework', 'concept', 
            'method', 'policy_based', 'value_based', 'hybrid',
            'algorithm', 'variant', 'improvement', 'base_algorithm',
            'domain', 'benchmark', 'field'
        }
        self.valid_layers = {
            'foundation', 'theoretical', 'algorithmic', 'implementation'
        }

    def extract_pdf_text(self, pdf_file) -> str:
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            return ""

    def generate_synthesis(self, text: str) -> str:
        """Generate a synthesis of the paper."""
        prompt = """Analyze this research paper and provide a comprehensive synthesis with the following sections:

1. Key Findings
- Main discoveries and contributions
- Significance in the field

2. Methods
- Key methodological approaches
- Technical innovations
- Implementation details

3. Results and Analysis
- Main experimental results
- Performance metrics
- Comparative analysis

4. Implications and Future Work
- Theoretical and practical implications
- Suggested future research directions
- Potential applications

Please structure the response clearly with headers and bullet points.

Paper text:
{text}
"""
        try:
            completion = self.client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                messages=[{
                    "role": "user",
                    "content": prompt.format(text=text[:8000])
                }],
                temperature=0.3,
                max_tokens=2048
            )
            
            if completion.choices:
                return completion.choices[0].message.content
            return "Could not generate synthesis."
            
        except Exception as e:
            st.error(f"Error generating synthesis: {e}")
            return "Error generating synthesis."

    def create_extract_prompt(self, text: str, article_reference: str) -> str:
        type_options = "|".join(self.valid_types)
        layer_options = "|".join(self.valid_layers)
        
        return f"""Extract key reinforcement learning entities from this scientific article.
Focus on identifying concepts, methods, or algorithms while maintaining consistency with existing knowledge organization.

Format as JSON:
{{
    "entities": [
        {{
            "id": "unique_snake_case_id",
            "name": "Full Name",
            "type": "{type_options}",
            "definition": "Clear, precise definition under 50 words",
            "domains": ["reinforcement_learning"],
            "properties": [
                {{
                    "name": "layer",
                    "value": "{layer_options}"
                }},
                {{
                    "name": "key_contribution",
                    "value": "Main insight or improvement"
                }},
                {{
                    "name": "scientific_paper",
                    "value": "{article_reference}"  
                }}
            ]
        }}
    ]
}}

Important guidelines:
1. Use ONLY the specified types and layers listed above
2. Skip mathematical formulations and equations
3. Focus on high-level concepts and their practical implications
4. Each entity must have a layer property
5. Keep definitions concise and clear

Text to analyze:
{text[:8000]}

Return ONLY the JSON object with no additional text or formatting."""

    def clean_json_response(self, response_text: str) -> dict:
        """Clean and parse JSON from API response."""
        try:
            # First attempt: direct JSON parsing
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass

            # Second attempt: find JSON between curly braces
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # Third attempt: clean up common issues and try again
            cleaned_text = response_text.strip()
            cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
            cleaned_text = re.sub(r'```\s*', '', cleaned_text)
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = json_str.encode('utf-8').decode('unicode_escape')
                return json.loads(json_str)

            st.error(f"Could not parse JSON response. Raw response:\n{response_text[:500]}...")
            return {"entities": []}

        except Exception as e:
            st.error(f"Error cleaning JSON: {str(e)}")
            return {"entities": []}

    def extract_entities(self, pdf_file) -> Dict:
        """Extract entities from the PDF."""
        text = self.extract_pdf_text(pdf_file)
        if not text:
            return {}
            
        article_reference = pdf_file.name
        
        with st.spinner("Extracting entities from the paper..."):
            try:
                completion = self.client.chat.completions.create(
                    model="nvidia/llama-3.1-nemotron-70b-instruct",
                    messages=[{
                        "role": "user",
                        "content": self.create_extract_prompt(text, article_reference)
                    }],
                    temperature=0.3,
                    max_tokens=2048
                )
                
                if not completion.choices:
                    st.error("No response received from API")
                    return {}
                    
                response = completion.choices[0].message.content
                return self.clean_json_response(response)
                
            except Exception as e:
                st.error(f"Error extracting entities: {str(e)}")
                return {}

    def create_relationship_prompt(self, entities: Dict) -> str:
        """Create prompt for relationship extraction."""
        return f"""Identify relationships between these entities, focusing on type and direction.

Entities:
{json.dumps(entities, indent=2)}

Return ONLY JSON in this format with no additional text:
{{
    "relationships": [
        {{
            "source": "source_entity_id",
            "target": "target_entity_id",
            "type": "relationship_type",
            "direction": "up|down|same|across"
        }}
    ]
}}

Direction guidelines:
- "up" for relationships to higher layers
- "down" for relationships to lower layers
- "same" for relationships within the same layer
- "across" for cross-layer relationships"""

    def extract_relationships(self, entities: Dict) -> Dict:
        """Extract relationships between entities."""
        with st.spinner("Extracting relationships between entities..."):
            try:
                completion = self.client.chat.completions.create(
                    model="nvidia/llama-3.1-nemotron-70b-instruct",
                    messages=[{
                        "role": "user",
                        "content": self.create_relationship_prompt(entities)
                    }],
                    temperature=0.3,
                    max_tokens=2048
                )
                
                if not completion.choices:
                    st.error("No response received from API")
                    return {}
                    
                response = completion.choices[0].message.content
                return self.clean_json_response(response)
                
            except Exception as e:
                st.error(f"Error extracting relationships: {str(e)}")
                return {}

    def create_graph(self, entities: Dict, relationships: Dict) -> nx.DiGraph:
        """Create a NetworkX graph from entities and relationships."""
        G = nx.DiGraph()
        
        # Add nodes
        for entity_id, entity in entities.items():
            G.add_node(entity_id, 
                      name=entity['name'],
                      type=entity['type'],
                      definition=entity.get('definition', ''))
        
        # Add edges
        for rel in relationships.get('relationships', []):
            G.add_edge(rel['source'], 
                      rel['target'],
                      type=rel['type'],
                      direction=rel['direction'])
        
        return G

    def visualize_graph(self, G: nx.DiGraph):
        """Create a visualization of the graph."""
        plt.figure(figsize=(12, 8))
        plt.style.use('classic')
        
        pos = nx.spring_layout(G, k=1.5, iterations=50)
        
        # Draw nodes with improved styling
        node_colors = ['#E3F2FD' if G.nodes[node]['type'] == 'concept'
                      else '#F3E5F5' if G.nodes[node]['type'] == 'algorithm'
                      else '#E8F5E9' for node in G.nodes()]
        
        nx.draw_networkx_nodes(G, pos, 
                             node_size=2500,
                             node_color=node_colors,
                             edgecolors='#2C3E50',
                             linewidths=1,
                             alpha=0.9)
        
        # Draw edges with curved arrows
        nx.draw_networkx_edges(G, pos, 
                             edge_color='#2C3E50',
                             arrows=True,
                             arrowsize=20,
                             connectionstyle='arc3,rad=0.2',
                             alpha=0.6)
        
        # Add labels with improved fonts
        labels = nx.get_node_attributes(G, 'name')
        nx.draw_networkx_labels(G, pos, labels, 
                              font_size=9,
                              font_family='sans-serif',
                              font_weight='medium')
        
        # Add edge labels with better positioning
        edge_labels = nx.get_edge_attributes(G, 'type')
        nx.draw_networkx_edge_labels(G, pos, edge_labels,
                                   font_size=7,
                                   font_family='sans-serif',
                                   alpha=0.7)
        
        plt.title("RL Knowledge Graph", pad=20, fontsize=14, fontweight='bold')
        plt.axis('off')
        return plt

def main():
    st.title("Research Paper Analyzer for Reinforcement Learning")
    
    st.markdown("""
    <div class="section-header">
        This tool helps you analyze reinforcement learning research papers by:
        <ul>
            <li>Generating a comprehensive synthesis</li>
            <li>Extracting key concepts and relationships</li>
            <li>Visualizing the knowledge graph</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        analyzer = RLPaperAnalyzer()
        text = analyzer.extract_pdf_text(uploaded_file)
        
        if text:
            # Generate and display synthesis
            with st.spinner("Generating paper synthesis..."):
                synthesis = analyzer.generate_synthesis(text)
                
            st.markdown('<h2 class="section-header">📑 Paper Synthesis</h2>', unsafe_allow_html=True)
            st.markdown(f'<div class="markdown-text">{synthesis}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Process entities and relationships
            with st.spinner("Extracting concepts and relationships..."):
                entities = analyzer.extract_entities(uploaded_file)
                
                if entities and 'entities' in entities:
                    st.markdown('<h2 class="section-header">🔍 Extracted Knowledge</h2>', unsafe_allow_html=True)
                    st.success(f"Found {len(entities['entities'])} concepts")
                    
                    entities_dict = {entity['id']: entity for entity in entities['entities']}
                    
                    with st.expander("📋 View Extracted Concepts"):
                        st.markdown('<div style="background-color: white; color: black; padding: 10px; border-radius: 5px;">', unsafe_allow_html=True)
                        st.json(entities)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    relationships = analyzer.extract_relationships(entities_dict)
                    if relationships and 'relationships' in relationships:
                        st.success(f"Found {len(relationships['relationships'])} relationships")
                        
                        with st.expander("🔗 View Relationships"):
                            st.json(relationships)
                        
                        st.markdown('<h2 class="section-header">📊 Knowledge Graph</h2>', unsafe_allow_html=True)
                        G = analyzer.create_graph(entities_dict, relationships)
                        fig = analyzer.visualize_graph(G)
                        st.pyplot(fig)
                        
                        st.markdown('<h2 class="section-header">💾 Download Results</h2>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Download Concepts (JSON)",
                                data=json.dumps(entities, indent=2),
                                file_name="concepts.json",
                                mime="application/json"
                            )
                        with col2:
                            st.download_button(
                                "📥 Download Relationships (JSON)",
                                data=json.dumps(relationships, indent=2),
                                file_name="relationships.json",
                                mime="application/json"
                            )

if __name__ == "__main__":
    main()