Building the Base Knowledge Graph
=================================

.. note::
   View the complete implementation in Google Colab: Open Notebook `Book Processing Implementation <https://colab.research.google.com/github/MasrourTawfik/Textra_research_v1/blob/main/documentation/docs/notebooks/book_processing.ipynb>`_


Initial Approach
-----------------
Our initial approach focused on using regular expressions to identify chapter and section boundaries. While this worked well for chapters, it proved problematic for sections.

Chapter Processing
~~~~~~~~~~~~~~~~~~~
The chapter identification pattern successfully matched chapter starts:

.. code-block:: python

    self.chapter_pattern = re.compile(
        r'^Chapter\s+(\d+)\s*$\s*([^\n]+)', 
        re.MULTILINE
    )

This pattern worked because:
- Chapter starts were consistent ("Chapter X")
- Chapter titles were on the next line
- Format was uniform throughout the book

Section Processing Challenges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The initial section processing attempted to use decimal notation:

.. code-block:: python

    self.section_pattern = re.compile(
        r'^(\d+\.\d+)\s+([^\n]+)'
    )

This approach failed because:
- Decimal notation appeared in equations
- Section numbers that are reference mid text
- PDF extraction introduced inconsistent spacing

Unicode and Text Cleaning
--------------------------
Before tackling section extraction, we implemented comprehensive text cleaning:

.. code-block:: python

    class TextCleaner:
        def __init__(self):
            # Unicode replacements
            self.unicode_map = {
                '\ufb01': 'fi',  # fi ligature
                '\ufb02': 'fl',  # fl ligature
                '\u21b5': 'ff',  # ↵ to ff
                # ... many more mappings
            }
            
            self.text_replacements = {
                'NUL': 'ffi',  # Common NUL replacement
                '  ': ' ',     # Double spaces
                # ... other patterns
            }

The cleaning process:
1. Unicode character normalization
2. Common pattern replacement
3. Whitespace normalization
4. Special character handling

Improved Section Processing
----------------------------
We revised our approach to use section titles as anchors:

.. code-block:: python

    def find_section_boundaries(content: str, sections: Dict[str, str]) -> Dict[str, Tuple[int, int]]:
        boundaries = {}
        ordered_sections = sorted(sections.keys())
        
        for i, section_num in enumerate(ordered_sections):
            section_title = sections[section_num]
            safe_title = re.escape(section_title)
            pattern = rf"{re.escape(section_num)}\s*{safe_title}"
            match = re.search(pattern, content)
            
            if match:
                start_pos = match.start()
                end_pos = len(content)
                
                if i < len(ordered_sections) - 1:
                    next_section = ordered_sections[i + 1]
                    next_title = sections[next_section]
                    next_pattern = rf"{re.escape(next_section)}\s*{re.escape(next_title)}"
                    next_match = re.search(next_pattern, content)
                    if next_match:
                        end_pos = next_match.start()
                
                boundaries[section_num] = (start_pos, end_pos)

improvements made:
- Use of metadata to identify correct section titles
- Escaped special characters in titles
- Sequential processing using next section as boundary

Final Processing Pipeline
-----------------------
The complete processing flow:

1. Initial PDF Text Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    def process_raw_chapters(base_dir: str = "./") -> None:
        cleaner = TextCleaner()
        for chapter_num in range(1, 17):
            # Read and clean chapter text
            cleaned_text = cleaner.clean(text)
            # Save as JSON with metadata

2. Section Boundary Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    def process_sections(base_dir: str = "./") -> None:
        for chapter_num in range(1, 17):
            # Load chapter content and metadata
            section_boundaries = find_section_boundaries(
                content, 
                metadata["sections"]
            )
            # Extract and save sections

output:
.. code-block:: None
    Reading PDF...

    ...
    
    Processed Chapter 01
    Title: Introduction
    Sections found:
    1.1: 10761 characters
    1.2: 4220 characters
    1.3: 4874 characters
    1.4: 3451 characters
    1.5: 15546 characters
    1.6: 1410 characters
    1.7: 33870 characters

    ...

    Processed Chapter 01: Introduction
    Found 7 sections
    Processed Chapter 02: Multi-armed Bandits
    Found 9 sections
    Processed Chapter 03: Finite Markov Decision Processes
    Found 6 sections
    Processed Chapter 04: Dynamic Programming
    Found 7 sections
    Processed Chapter 05: Monte Carlo Methods
    Found 7 sections
    Processed Chapter 06: Temporal-Difference Learning
    Found 8 sections
    Processed Chapter 07: n-step Bootstrapping
    Found 5 sections
    Processed Chapter 08: Planning and Learning with Tabular Methods
    Found 13 sections
    Processed Chapter 09: On-policy Prediction with Approximation
    Found 11 sections
    Processed Chapter 10: On-policy Control with Approximation
    Found 5 sections
    Processed Chapter 11: *Off-policy Methods with Approximation
    Found 9 sections
    Processed Chapter 12: Policy Gradient Methods
    Found 7 sections
    Processed Chapter 13: Psychology
    ...
    Processed Chapter 15: Applications and Case Studies
    Found 6 sections
    Processed Chapter 16: Frontiers
    Found 5 sections




Output Structure
-----------------
The final processing creates three versions of each chapter:

1. Raw Text (``chapter_XX.txt``)
   - Original PDF extraction

2. Cleaned Text (``chapter_XX_raw.json``)
   - Unicode normalized
   - Pattern replacements
   - Whitespace cleaned

3. Processed Sections (``chapter_XX_sections.json``)
   - Title and metadata
   - Individual section content
   - Properly bounded sections

Example Output
~~~~~~~~~~~~~~
.. code-block:: json

    {
      "title": "Introduction",
      "sections": {
        "1.1": {
          "title": "Reinforcement Learning",
          "content": "..." 
        },
        "1.2": {
          "title": "Examples",
          "content": "..."
        }
      }
    }

.. note::
   The section processing approach achieved its core objective, with opportunities for future refinement in equation handling and automation. The current implementation though is good enough for the next phase.