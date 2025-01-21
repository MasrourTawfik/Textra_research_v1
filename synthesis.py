from openai import OpenAI
import json
from pathlib import Path
from typing import Dict, List, Optional

class PaperSynthesizer:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or "YOUR API KEY HERE"
        )

    def _create_section_prompt(self, section: Dict, content: str, visuals: List[Dict]) -> str:
        """Create prompt for synthesizing a section."""
        return f'''Write a concise section for a research paper synthesis following this plan:

Title: {section["title"]}
Key Points: {json.dumps(section["content_plan"]["key_points"])}
Main Message: {section["content_plan"]["main_message"]}

Content: {content[:3000]}

Visuals to reference:
{json.dumps(visuals, indent=2)}

IMPORTANT: Be concise. Focus on key points. Integrate visuals naturally.
Return ONLY the section text in markdown format with appropriate headings and figure references.'''

    def _find_visuals(self, paths: List[str], media_analysis: List[Dict]) -> List[Dict]:
        """Find visual details from media analysis."""
        return [
            media for media in media_analysis 
            if media["path"] in paths
        ]

    def generate_section(self, section: Dict, content: str, media_analysis: List[Dict]) -> str:
        """Generate a single section of the synthesis."""
        try:
            # Get relevant visuals
            visuals = self._find_visuals(
                [v["media_path"] for v in section["content_plan"]["visual_elements"]], 
                media_analysis
            )
            
            # Generate content
            prompt = self._create_section_prompt(section, content, visuals)
            response = self.client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating section {section['title']}: {str(e)}")
            return f"## {section['title']}\nError generating content."

    def synthesize_paper(self, plan: Dict, paper_content: str) -> str:
        """Generate complete paper synthesis."""
        synthesis = []
        
        # Add metadata section
        metadata = plan["metadata"]
        # Create metadata section
        title = f"# {metadata['title']}\n\n"
        objective = f"**Main Objective**: {metadata['main_objective']}\n\n"
        contributions = "**Key Contributions**:\n" + "\n".join(f"- {contrib}" for contrib in metadata["key_contributions"])
        
        synthesis.append(f"{title}{objective}{contributions}")

        # Generate each section in sequence
        sections = {s["section_id"]: s for s in plan["synthesis_structure"]["sections"]}
        for section_id in plan["synthesis_structure"]["flow"]["section_sequence"]:
            section = sections[section_id]
            content = self.generate_section(
                section,
                paper_content,
                plan.get("media_analysis", [])
            )
            synthesis.append(content)
            
            # Add transition if available
            if transition := plan["synthesis_structure"]["flow"]["transitions"].get(section_id):
                synthesis.append(f"\n{transition}\n")

        return "\n\n".join(synthesis)

def create_synthesis(plan_path: str, paper_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Create synthesis from plan and paper content."""
    try:
        # Load files
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)["paper_analysis"]["synthesis_plan"]
        
        with open(paper_path, 'r', encoding='utf-8') as f:
            paper_data = json.load(f)
            paper_content = " ".join(
                page.get("text", "") 
                for page in paper_data.get("pages", [])
            )

        # Generate synthesis
        synthesizer = PaperSynthesizer()
        synthesis = synthesizer.synthesize_paper(plan_data, paper_content)

        # Save if needed
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