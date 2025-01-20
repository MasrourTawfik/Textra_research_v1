from typing import Dict, List, Optional, Union, Tuple
import json
from pathlib import Path
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class FigureInfo:
    path: str
    description: str
    caption: str = ""

class SynthesisGenerator:
    def __init__(self, api_key: str = None):
        """Initialize with NVIDIA API client."""
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or "ur api key here"
        )
        self.toc = None
        self.content = None
        self.figures = {}
        self.synthesis_data = {"sections": []}

    def load_files(self, toc_path: str, content_path: str):
        """Load TOC and content files."""
        with open(toc_path, 'r', encoding='utf-8') as f:
            self.toc = json.load(f)
        with open(content_path, 'r', encoding='utf-8') as f:
            self.content = json.load(f)
        self._extract_figures()

    def _extract_figures(self):
        """Extract figures and their descriptions from content."""
        for page in self.content.get("pages", []):
            for figure in page.get("figures", []):
                if figure.get("file_path"):
                    self.figures[figure["file_path"]] = FigureInfo(
                        path=figure["file_path"],
                        description=figure.get("description", ""),
                        caption=figure.get("caption", "")
                    )

    def _create_section_prompt(self, section: Dict, content: str) -> str:
        """Create prompt for LLaMA to generate section content."""
        return f"""Generate a detailed synthesis for the following section of a research paper:

Section Title: {section['title']}

Key Points to Cover:
{json.dumps(section['key_points'], indent=2)}

Content to Include:
{json.dumps(section['content_to_include'], indent=2)}

Relevant Paper Content:
{content}

Generate a comprehensive synthesis that:
1. Covers all key points listed
2. Integrates the relevant content provided
3. Maintains academic writing style
4. Is well-structured with clear paragraphs
5. References any relevant figures when appropriate ({', '.join(section['relevant_visuals'])})

Return the synthesis in markdown format with appropriate headers and formatting."""

    def _extract_content_for_section(self, section: Dict) -> str:
        """Extract relevant content from paper for a given section."""
        relevant_content = []
        keywords = set([
            *section["title"].lower().split(),
            *[point.lower() for point in section["key_points"]],
            *[content.lower() for content in section["content_to_include"]]
        ])
        
        for page in self.content.get("pages", []):
            text = page.get("text", "")
            paragraphs = text.split("\n\n")
            
            for paragraph in paragraphs:
                if any(keyword in paragraph.lower() for keyword in keywords):
                    relevant_content.append(paragraph)
        
        return "\n\n".join(relevant_content)

    def generate_section_content(self, section: Dict) -> Tuple[str, List[str]]:
        """Generate content for a single section using LLaMA."""
        content = self._extract_content_for_section(section)
        prompt = self._create_section_prompt(section, content)

        try:
            response = self.client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.3,
                max_tokens=2048
            )
            
            # Add to synthesis data
            self.synthesis_data["sections"].append({
                "title": section["title"],
                "content": response.choices[0].message.content,
                "relevant_visuals": section["relevant_visuals"]
            })
            
            return response.choices[0].message.content, section["relevant_visuals"]
        except Exception as e:
            print(f"Error generating content for section {section['title']}: {e}")
            error_content = f"## {section['title']}\nError generating content."
            self.synthesis_data["sections"].append({
                "title": section["title"],
                "content": error_content,
                "relevant_visuals": section["relevant_visuals"]
            })
            return error_content, []

    def generate_full_synthesis(self) -> str:
        """Generate complete synthesis following TOC structure."""
        if not self.toc or not self.content:
            raise ValueError("Please load files first using load_files()")

        synthesis = "# Article Synthesis\n\n"
        self.synthesis_data = {"sections": []}
        
        for section in self.toc["sections"]:
            content, _ = self.generate_section_content(section)
            synthesis += content + "\n\n"
            
        return synthesis

    def save_synthesis_json(self, output_path: str = "results/synthesis.json"):
        """Save synthesis data to JSON file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.synthesis_data, f, indent=2)

    def get_figure(self, figure_path: str) -> Optional[FigureInfo]:
        """Retrieve figure information by path."""
        return self.figures.get(figure_path)

    def get_relevant_figures(self, section_title: str) -> List[str]:
        """Get relevant figure paths for a section."""
        section = next((s for s in self.toc["sections"] if s["title"] == section_title), None)
        if section:
            return section["relevant_visuals"]
        return []

    def read_image_file(self, file_path: str) -> Optional[bytes]:
        """Read image file and return bytes."""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading image file {file_path}: {e}")
            return None

def create_synthesis(toc_path: str, content_path: str, api_key: str = None) -> Tuple[str, Dict[str, FigureInfo]]:
    """Create synthesis from TOC and content files."""
    generator = SynthesisGenerator(api_key)
    generator.load_files(toc_path, content_path)
    synthesis = generator.generate_full_synthesis()
    
    # Save synthesis to JSON
    generator.save_synthesis_json()
    
    return synthesis, generator.figures

# Example usage
if __name__ == "__main__":
    synthesis, figures = create_synthesis(
        toc_path="results/synthesis_toc.json",
        content_path="results/results_with_descriptions.json"
    )
    print(synthesis)
    
    # Print available figures
    print("\nAvailable Figures:")
    for path, info in figures.items():
        print(f"\nPath: {path}")
        print(f"Description: {info.description}")
        if info.caption:
            print(f"Caption: {info.caption}")