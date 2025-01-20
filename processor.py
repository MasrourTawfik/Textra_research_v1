from openai import OpenAI
import json
from pathlib import Path
from typing import Dict, List, Optional
import re

class SynthesisTOCGenerator:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or "ur api key here"
        )

    def create_analysis_prompt(self, paper_content: Dict) -> str:
        # Extract abstract
        abstract = ""
        if paper_content.get("pages"):
            text = paper_content["pages"][0].get("text", "")
            if "Abstract" in text:
                abstract = text.split("Abstract—")[1].split("\n\n")[0].strip()

        # Format figures information
        figures_text = ""
        for page in paper_content.get("pages", []):
            for figure in page.get("figures", []):
                if figure.get("description"):
                    figures_text += f"\nFigure ({figure['file_path']}):\n{figure['description']}\n"

        prompt = f"""Based on the provided research paper content, create a detailed Table of Contents for a synthesis. 
The synthesis should highlight the key aspects of the research in a structured way.

Here is the paper content with figures and their descriptions:

Abstract:
{abstract}

Available Figures and Their Analysis:
{figures_text}

Create a structured Table of Contents that:
1. Identifies main sections needed for synthesis
2. For each section, explain what content should be included
3. Indicate which figures/tables would be most relevant for each section
4. Highlight key points that should be emphasized

Return ONLY a JSON object with this structure (no markdown, no code blocks, no additional text):
{{
    "sections": [
        {{
            "title": "section name",
            "key_points": ["point 1", "point 2"],
            "content_to_include": ["content 1", "content 2"],
            "relevant_visuals": ["figure_path1", "figure_path2"]
        }}
    ]
}}"""

        return prompt

    def clean_llama_response(self, response: str) -> str:
        """Clean LLaMA response by removing markdown and extracting JSON."""
        # Remove markdown code blocks if present
        response = re.sub(r'^```(?:json)?\s*|\s*```$', '', response.strip())
        
        # Remove any leading/trailing whitespace
        response = response.strip()
        
        return response

    def generate_toc(self, paper_content: Dict) -> Optional[Dict]:
        """Generate TOC using LLaMA with enhanced error handling"""
        prompt = self.create_analysis_prompt(paper_content)

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

            # Clean and parse LLaMA's response
            cleaned_response = self.clean_llama_response(response.choices[0].message.content)
            
            try:
                toc = json.loads(cleaned_response)
                
                # Validate the expected structure
                if not isinstance(toc, dict) or "sections" not in toc:
                    raise ValueError("Response missing required 'sections' key")
                
                return toc
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print("Cleaned response:", cleaned_response)
                return None
                
            except ValueError as e:
                print(f"Invalid response structure: {e}")
                return None
                
        except Exception as e:
            print(f"Error generating TOC: {e}")
            return None

def create_synthesis_toc(paper_json_path: str, api_key: str = None) -> Optional[Dict]:
    """Create synthesis TOC from paper content using LLaMA"""
    try:
        # Load paper content
        with open(paper_json_path, 'r', encoding='utf-8') as f:
            paper_content = json.load(f)

        # Generate TOC
        generator = SynthesisTOCGenerator(api_key)
        toc = generator.generate_toc(paper_content)

        # Save TOC if generated successfully
        if toc:
            output_path = Path(paper_json_path).parent / "synthesis_toc.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(toc, f, indent=2)
            return toc
        
        return None

    except FileNotFoundError:
        print(f"Error: Could not find paper content file at {paper_json_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in paper content file at {paper_json_path}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    paper_path = "results/results_with_descriptions.json"
    toc = create_synthesis_toc(paper_path)
    if toc:
        print(json.dumps(toc, indent=2))
    else:
        print("Failed to generate TOC")