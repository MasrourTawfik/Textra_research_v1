import json
from enum import Enum
from typing import Dict, List, Optional

class LearningStyle(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"

class ContentGenerator:
    def __init__(self, learning_style: LearningStyle):
        self.learning_style = learning_style
        
    def _analyze_media_importance(self, item: Dict) -> float:
        """Calculate importance score for media items."""
        score = 0.0
        description = item.get('description', '').lower()
        context = item.get('reference_text', '').lower()
        
        key_terms = ['key', 'main', 'significant', 'demonstrates', 'result']
        score += sum(0.2 for term in key_terms if term in description or term in context)
        
        if item.get('context_found', False):
            score += 0.3
            
        return min(score, 1.0)

    def _should_display_media(self) -> bool:
        """Determine if media should be displayed based on learning style."""
        return self.learning_style in [
            LearningStyle.VISUAL,
            LearningStyle.KINESTHETIC
        ]

    def generate_toc(self, vision_output: Dict) -> Dict:
        """Generate table of contents based on vision analysis and learning style."""
        # Extract and analyze media items
        media_items = []
        for page in vision_output['pages']:
            for fig in page.get('figures', []):
                if 'description' in fig:
                    media_items.append({
                        'type': 'figure',
                        'description': fig['description'],
                        'context': fig.get('reference_text', ''),
                        'importance': self._analyze_media_importance(fig)
                    })
            for table in page.get('tables', []):
                if 'description' in table:
                    media_items.append({
                        'type': 'table',
                        'description': table['description'],
                        'context': table.get('reference_text', ''),
                        'importance': self._analyze_media_importance(table)
                    })

        # Sort media items by importance
        important_items = sorted(media_items, key=lambda x: x['importance'], reverse=True)

        # Generate sections based on learning style
        sections = []
        display_media = self._should_display_media()
        
        if self.learning_style == LearningStyle.VISUAL:
            sections = [
                {
                    "title": "Visual Overview and Key Concepts",
                    "content": "Start with main diagrams and charts to build foundational understanding. Focus on visual relationships between components.",
                    "display_media": True,
                    "order": 1
                },
                {
                    "title": "Detailed Visual Analysis",
                    "content": "Deep dive into specific figures and their interconnections. Use visual comparisons to highlight key differences.",
                    "display_media": True,
                    "order": 2
                },
                {
                    "title": "Visual Summary and Integration",
                    "content": "Connect all visual elements to form comprehensive understanding. Create visual mind maps of relationships.",
                    "display_media": True,
                    "order": 3
                }
            ]
            
        elif self.learning_style == LearningStyle.AUDITORY:
            sections = [
                {
                    "title": "Conceptual Introduction",
                    "content": "Verbal explanation of key concepts and their relationships. Focus on clear, descriptive language.",
                    "display_media": False,
                    "order": 1
                },
                {
                    "title": "Detailed Explanations",
                    "content": "In-depth verbal descriptions of methodologies and findings. Use analogies and verbal examples.",
                    "display_media": False,
                    "order": 2
                },
                {
                    "title": "Verbal Analysis and Discussion",
                    "content": "Discussion-style exploration of implications and connections. Emphasis on verbal reasoning.",
                    "display_media": False,
                    "order": 3
                }
            ]
            
        elif self.learning_style == LearningStyle.KINESTHETIC:
            sections = [
                {
                    "title": "Hands-on Introduction",
                    "content": "Interactive exploration of key concepts through practical examples and exercises.",
                    "display_media": True,
                    "order": 1
                },
                {
                    "title": "Applied Practice",
                    "content": "Step-by-step practical application of concepts. Include interactive exercises and real-world examples.",
                    "display_media": True,
                    "order": 2
                },
                {
                    "title": "Practical Integration Project",
                    "content": "Hands-on project combining all learned concepts. Focus on practical implementation.",
                    "display_media": True,
                    "order": 3
                }
            ]
            
        elif self.learning_style == LearningStyle.READING_WRITING:
            sections = [
                {
                    "title": "Written Overview",
                    "content": "Comprehensive written introduction to key concepts and methodologies.",
                    "display_media": False,
                    "order": 1
                },
                {
                    "title": "Detailed Text Analysis",
                    "content": "In-depth written explanations and analysis of each component.",
                    "display_media": False,
                    "order": 2
                },
                {
                    "title": "Written Integration and Summary",
                    "content": "Written synthesis of concepts and their relationships. Include detailed notes and summaries.",
                    "display_media": False,
                    "order": 3
                }
            ]

        return {"sections": sections}

def create_learning_toc(vision_output: Dict, learning_style: str) -> Dict:
    """Helper function to create table of contents from vision analysis output."""
    try:
        # Convert learning style string to enum
        style = LearningStyle(learning_style.lower())
        
        # Create generator and generate TOC
        generator = ContentGenerator(style)
        return generator.generate_toc(vision_output)
        
    except Exception as e:
        print(f"Error generating table of contents: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    with open("results_with_descriptions.json", "r") as f:
        vision_output = json.load(f)
    
    learning_style = "visual" 
    toc = create_learning_toc(vision_output, learning_style)
    
    if toc:
        print(json.dumps(toc, indent=2))