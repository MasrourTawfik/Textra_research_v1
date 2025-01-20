ArXiv Papers Downloader
=======================

This module implements an ArXiv paper downloader specifically focused on retrieving reinforcement learning papers. It downloads the top 100 most relevant papers per year from 2017 onwards.

Dependencies
------------

.. code-block:: python

    import arxiv            # Interface with ArXiv API
    import json            # Handle metadata storage
    import os             # File operations
    from datetime import datetime
    import time           # to implement delays between requests
    from pathlib import Path    # Modern path manipulation
    import requests       # Handle HTTP requests
    from typing import Dict, List, Optional   # Type hints
    import logging        # Track operations and errors
    from urllib.parse import urlparse
    import traceback     # Detailed error tracking

notes:
- ``arxiv``: Python wrapper for ArXiv API (install using ``pip install arxiv``)
- ``pathlib``: Provides object-oriented interface to filesystem paths
- ``requests``: Used for downloading PDFs directly

Class Implementation
--------------------

The downloader is implemented as a class with multiple methods. Here's how to initialize it:

.. code-block:: python

    class ArxivDownloader:
        def __init__(self):
            """Initialize the ArXiv downloader with fixed paths"""
            # Set your paths here
            self.base_dir = Path("path/to/your/project")  # Replace with your project path
            self.base_path = self.base_dir / "data"
            self.pdfs_dir = self.base_path / "pdfs"
            self.metadata_dir = self.base_path / "metadata"
            
            self._setup_directories()
            self._setup_logging()

Directory Setup
~~~~~~~~~~~~~~~

This method creates the necessary directory structure:

.. code-block:: python

    def _setup_directories(self):
        """Create necessary directory structure"""
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Create year subdirectories
        current_year = datetime.now().year
        for year in range(2017, current_year + 1):
            (self.pdfs_dir / str(year)).mkdir(exist_ok=True)
            (self.metadata_dir / str(year)).mkdir(exist_ok=True)

Logging Configuration
~~~~~~~~~~~~~~~~~~~~~

Setup logging to track operations and errors:

.. code-block:: python

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.base_path / "download_log.txt"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

PDF Download Handler
~~~~~~~~~~~~~~~~~~~~~

Safe PDF download implementation:

.. code-block:: python

    def _safe_download_pdf(self, paper, pdf_path: Path) -> bool:
        """Safely download PDF with proper path handling"""
        try:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_url = next(str(link) for link in paper.links if 'pdf' in str(link))
            
            response = requests.get(pdf_url, allow_redirects=True)
            if response.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                return True
                
            self.logger.error(f"Failed to download PDF, status code: {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {str(e)}")
            return False

Papers Download
~~~~~~~~~~~~~~~

Main method to download papers for a specific year:

.. code-block:: python

    def download_papers(self, year: int):
        """Download exactly 100 papers for the specified year"""
        self.logger.info(f"\nStarting download for year {year}")
        
        # Construct search client
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=5
        )
        
        # Create search with max_results=100
        search = arxiv.Search(
            query=self._construct_query(year),
            max_results=100  # Limit to 100 papers
        )
        
        # Initialize metadata collection
        year_metadata = []
        papers_processed = 0
        
        try:
            # Collect exactly 100 papers
            papers = list(client.results(search))
            total_papers = len(papers)
            print(f"\nFound {total_papers} papers for {year}")
            
            if not papers:
                self.logger.warning(f"No papers found for year {year}")
                return 0
            
            # Process and download papers
            print(f"\nDownloading PDFs for year {year}:")
            for idx, paper in enumerate(papers, 1):
                paper_id = paper.entry_id.split('/')[-1].split('v')[0]  # Remove version number
                
                try:
                    # Extract and save metadata
                    metadata = self._extract_metadata(paper)
                    year_metadata.append(metadata)
                    
                    # Download PDF
                    pdf_path = self.pdfs_dir / str(year) / f"{paper_id}.pdf"
                    if not pdf_path.exists():
                        if self._safe_download_pdf(paper, pdf_path):
                            print(f"[{idx}/100] Downloaded: {paper.title[:50]}...")
                        else:
                            print(f"[{idx}/100] Failed to download: {paper.title[:50]}...")
                    else:
                        print(f"[{idx}/100] Already exists: {paper.title[:50]}...")
                    
                    time.sleep(1)  # Be nice to arXiv servers
                    
                except Exception as e:
                    self.logger.error(f"Error processing paper {paper_id}: {str(e)}")
                    continue
                
            # Save metadata for the year
            metadata_path = self.metadata_dir / str(year) / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(year_metadata, f, indent=2, ensure_ascii=False)
            
            print(f"\nYear {year} complete:")
            print(f"- PDFs downloaded: {len(year_metadata)}")
            print(f"- Metadata saved to: {metadata_path}")
            
            return len(year_metadata)
            
        except Exception as e:
            self.logger.error(f"Error downloading papers for year {year}: {str(e)}")
            return 0



Query Construction
~~~~~~~~~~~~~~~~~~

Construct ArXiv search query:

.. code-block:: python

    def _construct_query(self, year: int) -> str:
        """Construct arXiv query for RL papers from specific year"""
        return (f'(cat:cs.AI OR cat:cs.LG) AND '
                f'(abs:"reinforcement learning" OR abs:"deep reinforcement learning") AND '
                f'submittedDate:[{year}0101 TO {year}1231]')

Metadata Extraction
~~~~~~~~~~~~~~~~~~~

Extract paper metadata:

.. code-block:: python

    def _extract_metadata(self, paper) -> Dict:
        """Extract relevant metadata from arXiv paper"""
        return {
            'title': paper.title,
            'authors': [str(author) for author in paper.authors],
            'abstract': paper.summary,
            'categories': paper.categories,
            'published': paper.published.strftime('%Y-%m-%d'),
            'updated': paper.updated.strftime('%Y-%m-%d'),
            'arxiv_id': paper.entry_id.split('/')[-1],
            'primary_category': paper.primary_category,
            'doi': paper.doi,
            'links': [str(link) for link in paper.links]
        }

Running the Downloader
----------------------

To use the downloader:

.. code-block:: python

    # Initialize the downloader
    downloader = ArxivDownloader()

    # Start downloading papers from 2017 to current year
    downloader.download_all_years(start_year=2017)

Experimentation Tips
---------------------

1. To experiment with different years:
   - Modify the ``start_year`` parameter when calling ``download_all_years()``
   - You can also download papers for a single year using ``download_papers(year)``

2. To modify the search criteria:
   - Adjust the ``_construct_query()`` method to change search terms or categories
   - Add or remove ArXiv categories (e.g., add 'cs.NE' for Neural and Evolutionary Computing)

3. To customize the metadata:
   - Modify the ``_extract_metadata()`` method to add or remove fields
   - You can add custom fields like citation count if you integrate with other APIs

4. To adjust download behavior:
   - Modify the delay between downloads in ``download_papers()`` (currently 1 second)
   - Change the delay between years in ``download_all_years()`` (currently 5 seconds)