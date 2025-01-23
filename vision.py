import json
import requests
import base64
from pathlib import Path
import time
import re

class VisionAnalyzer:
    def __init__(self, api_key):
        """Initialize the vision analyzer with API key"""
        self.api_key = "Your api key here"
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

    def find_media_reference(self, text, media_type, page_num):
        """Find reference to a specific figure/table in text"""
        # Broader patterns for finding references
        patterns = [
            f"{media_type}\.?\s*{page_num}",           # Fig. 1 or Table 1
            f"{media_type}\.?\s*\[{page_num}\]",       # Fig. [1] or Table [1]
            f"{media_type}\.?\s*\({page_num}\)",       # Fig. (1) or Table (1)
            f"(?:see|in)\s+{media_type}\.?\s*{page_num}",  # see Fig. 1 or in Table 1
        ]
        
        # Get all matches from all patterns
        contexts = []
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                # Get wider context around match
                start = max(0, match.start() - 1000)
                end = min(len(text), match.end() + 1000)
                
                # Find sentence boundaries
                context_text = text[start:end]
                sentences = re.split(r'(?<=[.!?])\s+', context_text)
                
                # Get sentences containing and surrounding the match
                match_pos = match.start() - start
                for i, sentence in enumerate(sentences):
                    if match_pos <= len(sentence):
                        # Get surrounding sentences
                        start_idx = max(0, i - 2)
                        end_idx = min(len(sentences), i + 3)
                        context = ' '.join(sentences[start_idx:end_idx])
                        contexts.append(context)
                        break
                    match_pos -= len(sentence) + 1
                    
        return ' '.join(contexts) if contexts else text

    def get_page_context(self, pages, current_page_num):
        """Get context from current and adjacent pages"""
        context_text = []
        
        # Get text from previous, current, and next page
        for page in pages:
            if abs(page['page_num'] - current_page_num) <= 1:  # Include adjacent pages
                if 'text' in page:
                    context_text.append(page['text'])
                    
        return '\n'.join(context_text)

    def analyze_image(self, image_path, pages, current_page, media_type, page_num):
        """Analyze a single image with document context"""
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()

            # Check size limit
            if len(image_b64) >= 180_000:
                print(f"Warning: Image {image_path} is too large (>180KB)")
                return None

            # Get context but limit it to ~500 characters to avoid token limit
            page_context = self.get_page_context(pages, current_page['page_num'])
            reference_context = self.find_media_reference(page_context, media_type, page_num)
            truncated_context = reference_context[:500] + "..." if len(reference_context) > 500 else reference_context
            
            # Prepare different prompts for figures and tables
            if media_type.lower() == 'figure':
                prompt = f"""Based on this figure and the surrounding text, provide a concise analysis:

    Context: {truncated_context}

    1. Contextual Placement:
    - How this figure relates to the text passage
    - Its role in the current section

    2. Technical Analysis:
    - Main elements and structure
    - Key metrics or patterns shown
    - Mathematical or algorithmic aspects

    3. Research Impact:
    - Main findings illustrated
    - Contribution to methodology/results

    Please be specific and technical in your analysis."""

            else:  # Table
                prompt = f"""Based on this table and the surrounding text, provide a concise analysis:

    Context: {truncated_context}

    1. Data Organization:
    - Structure and content overview
    - Key metrics presented

    2. Critical Findings:
    - Notable patterns or values
    - Statistical significance

    3. Research Value:
    - Support for paper's claims
    - Methodological insights

    Please focus on key data points and findings."""

            payload = {
                "model": 'microsoft/phi-3.5-vision-instruct',
                "messages": [
                    {
                        "role": "user",
                        "content": f'{prompt} <img src="data:image/jpeg;base64,{image_b64}" />'
                    }
                ],
                "max_tokens": 512,
                "temperature": 0.20,
                "top_p": 0.70,
                "stream": False
            }

            response = requests.post(self.invoke_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return {
                        'description': result['choices'][0]['message']['content'],
                        'context_used': True,
                        'reference_text': truncated_context
                    }
            
            print(f"Error analyzing image {image_path}: {response.text}")
            return None

        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return None
    def process_results_file(self, results_path):
        """Process a results.json file and add descriptions to all images"""
        try:
            # Load results file
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            print(f"Processing results from: {results_path}")
            
            # Process each page
            for page in results['pages']:
                page_num = page['page_num']
                print(f"\nProcessing page {page_num}")

                # Process tables
                for i, table in enumerate(page['tables'], 1):
                    if 'file_path' in table:
                        print(f"Analyzing table {i} on page {page_num}")
                        analysis = self.analyze_image(
                            table['file_path'],
                            results['pages'],  # Pass all pages for context
                            page,
                            "Table",
                            i
                        )
                        if analysis:
                            table['description'] = analysis['description']
                            table['context_found'] = analysis['context_used']
                            table['reference_text'] = analysis['reference_text']
                            time.sleep(1)  # Rate limiting

                # Process figures
                for i, figure in enumerate(page['figures'], 1):
                    if 'file_path' in figure:
                        print(f"Analyzing figure {i} on page {page_num}")
                        analysis = self.analyze_image(
                            figure['file_path'],
                            results['pages'],  # Pass all pages for context
                            page,
                            "Figure",
                            i
                        )
                        if analysis:
                            figure['description'] = analysis['description']
                            figure['context_found'] = analysis['context_used']
                            figure['reference_text'] = analysis['reference_text']
                            time.sleep(1)  # Rate limiting

            # Save updated results
            output_path = Path(results_path).parent / 'results_with_descriptions.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            print(f"\nAnalysis complete! Results saved to: {output_path}")
            return results

        except Exception as e:
            print(f"Error processing results file: {e}")
            return None


def analyze_paper_media(results_path, api_key):
    """Helper function to analyze media in a paper's results"""
    analyzer = VisionAnalyzer(api_key)
    return analyzer.process_results_file(results_path)

if __name__ == "__main__":
    # Example usage
    API_KEY = "Your api key here"
    results_path = "results/results.json"
    
    results = analyze_paper_media(results_path, API_KEY)
    if results:
        print("\nSummary:")
        total_with_context = 0
        for page in results['pages']:
            print(f"\nPage {page['page_num']}:")
            tables_with_context = len([t for t in page['tables'] if t.get('context_found')])
            figures_with_context = len([f for f in page['figures'] if f.get('context_found')])
            print(f"Tables analyzed: {len(page['tables'])} ({tables_with_context} with context)")
            print(f"Figures analyzed: {len(page['figures'])} ({figures_with_context} with context)")
            total_with_context += tables_with_context + figures_with_context