from openai import OpenAI
import json
from pathlib import Path
from typing import Dict, List, Optional

class PaperSynthesizer:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or "Your api key here"
        )

    def _create_section_prompt(self, section: Dict, content: str, visuals: List[Dict]) -> str:
        """Create prompt for synthesizing a section without instructions in output."""
        # Extract figure numbers for cleaner references
        visual_refs = []
        for v in visuals:
            if path_parts := v.get('path', '').split('_'):
                if len(path_parts) > 1 and path_parts[1].isdigit():
                    visual_refs.append(f"{v.get('type', 'Figure')} {path_parts[1]}")

        return f'''I want you to write Section {section["title"]} of a research paper in academic prose.

Here is the content to cover:
{content[:3000]}

Main points:
{json.dumps(section["content_plan"]["key_points"], indent=2)}

Core message:
{section["content_plan"]["main_message"]}

Available figures: {", ".join(visual_refs) if visual_refs else "None"}

Write this section in academic style, incorporating the available figures naturally where relevant.'''

    def generate_section(self, section: Dict, content: str, media_analysis: List[Dict]) -> str:
        """Generate a single section of the synthesis with no meta-text."""
        try:
            # Get relevant visuals
            visuals = self._find_visuals(
                [v["media_path"] for v in section["content_plan"]["visual_elements"]], 
                media_analysis
            )
            
            # Generate content with stronger system message
            prompt = self._create_section_prompt(section, content, visuals)
            response = self.client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are writing direct academic prose. Never include:
    - Instructions or notes about writing
    - Meta-commentary about what to include
    - Phrases like "let's discuss" or "now we'll show"
    - Text about what should be written
    Write only the final academic content as it would appear in the paper."""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            section_text = response.choices[0].message.content.strip()
            
            # Ensure section starts with header if not present
            if not section_text.startswith('#'):
                section_text = f"## {section['title']}\n\n{section_text}"
                
            return section_text
            
        except Exception as e:
            print(f"Error generating section {section['title']}: {str(e)}")
            return f"## {section['title']}\nError generating content."

    def synthesize_paper(self, plan: Dict, paper_content: str) -> str:
        """Generate complete paper synthesis."""
        synthesis = []
        
        # Create title and metadata section
        metadata = plan["metadata"]
        metadata_section = [
            f"# {metadata['title']}",
            "",
            f"**Main Objective**: {metadata['main_objective']}",
            "",
            "**Key Contributions**:"
        ]
        metadata_section.extend(f"- {contrib}" for contrib in metadata["key_contributions"])
        synthesis.append("\n".join(metadata_section))

        # Generate each section
        sections = {s["section_id"]: s for s in plan["synthesis_structure"]["sections"]}
        for i, section_id in enumerate(plan["synthesis_structure"]["flow"]["section_sequence"]):
            section = sections[section_id]
            
            # Pass context about position in document
            section_context = {
                "is_first": i == 0,
                "is_last": i == len(plan["synthesis_structure"]["flow"]["section_sequence"]) - 1,
                "previous_section": sections.get(plan["synthesis_structure"]["flow"]["section_sequence"][i-1]) if i > 0 else None,
                "next_section": sections.get(plan["synthesis_structure"]["flow"]["section_sequence"][i+1]) if i < len(plan["synthesis_structure"]["flow"]["section_sequence"]) - 1 else None
            }
            
            content = self.generate_section(
                {**section, "context": section_context},
                paper_content,
                plan.get("media_analysis", [])
            )
            
            synthesis.append(content)

        return "\n\n".join(synthesis)

    def _find_visuals(self, paths: List[str], media_analysis: List[Dict]) -> List[Dict]:
        """Find visual details from media analysis."""
        return [
            media for media in media_analysis 
            if media["path"] in paths
        ]

    
    
def create_synthesis(plan_path: str, paper_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Create synthesis from plan and paper content."""
    try:
        # Load and validate files
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
                if "paper_analysis" not in plan_data or "synthesis_plan" not in plan_data["paper_analysis"]:
                    raise ValueError("Invalid synthesis plan structure")
                plan_data = plan_data["paper_analysis"]["synthesis_plan"]
        except Exception as e:
            print(f"Error loading synthesis plan: {str(e)}")
            return None

        try:
            with open(paper_path, 'r', encoding='utf-8') as f:
                paper_data = json.load(f)
                if "pages" not in paper_data:
                    raise ValueError("Invalid paper content structure")
                paper_content = " ".join(
                    page.get("text", "").strip() 
                    for page in paper_data.get("pages", [])
                    if page.get("text")
                )
        except Exception as e:
            print(f"Error loading paper content: {str(e)}")
            return None

        # Generate synthesis
        synthesizer = PaperSynthesizer()
        synthesis = synthesizer.synthesize_paper(plan_data, paper_content)

        # Save output if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(synthesis)

        return synthesis

    except Exception as e:
        print(f"Error creating synthesis: {str(e)}")
        return None

if __name__ == "__main__":
    synthesis = create_synthesis(
        "results/synthesis_plan.json",
        "results/results_with_descriptions.json",
        "results/synthesis.md"
    )
    
    if synthesis:
        print("\nSynthesis complete!")
        print("Output saved to results/synthesis.md")