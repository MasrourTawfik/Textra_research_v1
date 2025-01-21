from openai import OpenAI
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

class PaperProcessor:
    def __init__(self, api_key: str = None):
        """Initialize processor with API key."""
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key or "YOUR API KEY HERE"
        )

    def _create_llm_analysis_prompt(self, media_type: str, description: str, context: str) -> str:
        """Create analysis prompt for media items."""
        return f'''Analyze this {media_type} to determine if it's essential for understanding the research paper.

Content to analyze:
Description: {description}
Context: {context}

IMPORTANT: Return ONLY the following JSON object with no additional text, no markdown, and no explanation:
{{
    "is_essential": true/false,
    "understanding_role": "brief explanation why this is/isn't essential",
    "placement_suggestion": "brief suggestion where to show this in synthesis"
}}'''

    def _create_synthesis_prompt(self, paper_text: str, essential_media: List[Dict]) -> str:
        """Create synthesis planning prompt."""
        return f'''Create a structured synthesis plan for this research paper.
The paper includes {len(essential_media)} essential visual elements that need to be integrated.

Paper Content:
{paper_text}

Essential Visuals:
{json.dumps(essential_media, indent=2)}

Create a detailed synthesis structure that effectively presents this research.

Return ONLY a JSON object with this exact structure:
{{
    "metadata": {{
        "title": "paper title",
        "main_objective": "paper's main goal",
        "key_contributions": ["list of main contributions"]
    }},
    "synthesis_structure": {{
        "sections": [
            {{
                "section_id": "unique_identifier",
                "title": "section title",
                "content_plan": {{
                    "key_points": ["points to cover"],
                    "main_message": "central message",
                    "required_context": ["needed content"],
                    "visual_elements": [
                        {{
                            "media_path": "path",
                            "purpose": "usage reason",
                            "integration_notes": "integration details"
                        }}
                    ]
                }}
            }}
        ],
        "flow": {{
            "section_sequence": ["section_ids"],
            "transitions": {{
                "section_id": "transition notes"
            }}
        }}
    }},
    "visual_integration": {{
        "essential_visuals": ["visual paths"],
        "presentation_order": ["ordered paths"],
        "integration_strategy": "integration approach"
    }}
}}'''

    def _call_llm(self, prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> Optional[Dict]:
        """Make LLM API call with error handling."""
        try:
            print("Sending request to LLM...")
            response = self.client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.8
            )
            
            if not response.choices:
                print("No choices in response")
                return None
                
            content = response.choices[0].message.content.strip()
            print("\nRaw LLM Response:")
            print(content)
            print("\nAttempting to parse JSON...")
            
            # Try to clean the response if it's wrapped in markdown code blocks
            if content.startswith("```") and content.endswith("```"):
                content = content.strip("```")
                if content.startswith("json"):
                    content = content[4:].strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON-like structure in the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    print("Could not find valid JSON in response")
                    return None
            
        except Exception as e:
            print(f"LLM API error: {str(e)}")
            print(f"Full error details: {type(e).__name__}")
            return None

    def analyze_media_item(self, item: Dict) -> Optional[Dict]:
        """Analyze a single media item."""
        try:
            if not item.get('description'):
                print(f"Skipping media item: no description available")
                return None
                
            media_type = "figure" if item.get('type') == 'figure' else "table"
            print(f"\nAnalyzing {media_type}...")
            
            prompt = self._create_llm_analysis_prompt(
                media_type,
                item.get('description', '').strip(),
                item.get('reference_text', '').strip()
            )
            
            analysis = self._call_llm(prompt)
            if not analysis:
                print(f"Could not analyze {media_type}, using default analysis")
                analysis = {
                    "is_essential": False,
                    "understanding_role": "Analysis failed - treating as non-essential",
                    "placement_suggestion": "N/A"
                }
                
            result = {
                "type": media_type,
                "path": item.get('file_path'),
                "content": {
                    "description": item.get('description', ''),
                    "reference_text": item.get('reference_text', '')
                },
                "analysis": analysis
            }
            
            print(f"Successfully analyzed {media_type}")
            return result
            
        except Exception as e:
            print(f"Error analyzing media item: {str(e)}")
            return None

    def analyze_all_media(self, content: Dict) -> List[Dict]:
        """Analyze all media items in the paper."""
        analyzed_items = []
        
        for page in content.get("pages", []):
            # Analyze figures
            for figure in page.get("figures", []):
                if analysis := self.analyze_media_item(figure):
                    analyzed_items.append(analysis)
                    
            # Analyze tables
            for table in page.get("tables", []):
                if analysis := self.analyze_media_item(table):
                    analyzed_items.append(analysis)
        
        return analyzed_items

    def create_synthesis_plan(self, content: Dict, analyzed_media: List[Dict]) -> Optional[Dict]:
        """Create synthesis plan using analyzed media."""
        # Get essential media
        essential_media = [
            item for item in analyzed_media 
            if item["analysis"].get("is_essential")
        ]
        
        # Create synthesis prompt
        paper_text = " ".join(
            page.get("text", "") 
            for page in content.get("pages", [])
        )[:3000]
        
        prompt = self._create_synthesis_prompt(paper_text, essential_media)
        return self._call_llm(prompt, temperature=0.3, max_tokens=2048)

    def process_paper(self, content: Dict) -> Optional[Dict]:
        """Process paper and create complete analysis."""
        try:
            # Step 1: Analyze media
            analyzed_media = self.analyze_all_media(content)
            if not analyzed_media:
                raise ValueError("No media could be analyzed")

            # Step 2: Create synthesis plan
            synthesis_plan = self.create_synthesis_plan(content, analyzed_media)
            if not synthesis_plan:
                raise ValueError("Could not create synthesis plan")

            # Step 3: Return structured result
            return {
                "version": "1.0",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "paper_analysis": {
                    "synthesis_plan": synthesis_plan,
                    "media_analysis": analyzed_media
                },
                "processing_metadata": {
                    "media_count": len(analyzed_media),
                    "essential_media_count": len([
                        m for m in analyzed_media 
                        if m["analysis"].get("is_essential")
                    ]),
                    "structure_version": "v1"
                }
            }

        except Exception as e:
            print(f"Error processing paper: {str(e)}")
            return None

def process_research_paper(input_path: str, output_path: Optional[str] = None) -> Optional[Dict]:
    """Process a research paper and save results."""
    try:
        # Load content
        with open(input_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        # Process
        processor = PaperProcessor()
        result = processor.process_paper(content)

        # Save if needed
        if result and output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)

        return result

    except Exception as e:
        print(f"Error in paper processing: {str(e)}")
        return None

if __name__ == "__main__":
    result = process_research_paper(
        "results/results_with_descriptions.json",
        "results/synthesis_plan.json"
    )
    
    if result:
        print("\nProcessing complete!")
        print(
            f"Found {result['processing_metadata']['essential_media_count']} "
            f"essential visuals out of {result['processing_metadata']['media_count']} "
            f"total media items"
        )