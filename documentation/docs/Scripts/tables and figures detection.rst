Layout Parser Implementation
=============================

.. note::
View the complete implementation in Google Colab: Open Notebook <https://colab.research.google.com/github/YOUR_USERNAME/YOUR_REPO/blob/main/documentation/notebooks/layoutparser_implementation.ipynb>_

Introduction
-------------
Layout Parser is a toolkit for Document Layout Analysis that helps detect and extract various elements from documents, including tables, figures, text blocks, and more. It uses deep learning models trained on large datasets like PubLayNet to identify different components in document images.

Installation
-------------
Install LayoutParser and its dependencies:

.. code-block:: bash

   pip install layoutparser
   pip install "detectron2@git+https://github.com/facebookresearch/detectron2.git@v0.5#egg=detectron2" #if you are encountring any problem with this installation refer to readme.md
   pip install "layoutparser[layoutmodels]"

Components
------------

Model Initialization
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    model = lp.Detectron2LayoutModel(
        'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", min(table_threshold, figure_threshold)],
        label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
    )

for customization:
- Modify ``label_map`` to detect different elements
- Adjust thresholds for detection sensitivity
- Use different pre-trained models (e.g., ``lp://PrimaLayout/mask_rcnn_R_50_FPN_3x`` for historical documents)

Block Type Detection
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def get_block_type(block):
        """Helper function to safely get block type from layout detection"""
        if hasattr(block, 'type'):
            return block.type
        
        if hasattr(block, 'label'):
            if isinstance(block.label, str):
                return block.label
            if isinstance(block.label, (int, float)):
                type_mapping = {
                    0: 'Text',
                    1: 'Title',
                    2: 'List',
                    3: 'Table',
                    4: 'Figure'
                }
                return type_mapping.get(int(block.label), 'Unknown')
        
        return 'Unknown'

for customization:
- Add new types to ``type_mapping``
- Modify return values for different classification needs
- Add custom type detection logic

Visualization
~~~~~~~~~~~~~

.. code-block:: python

    def create_visualization(image, detected_elements, show_plot=True):
        """Create visualization of detected tables and figures"""
        viz_image = image.copy()
        draw = ImageDraw.Draw(viz_image)
        
        # Customize colors and labels for different element types
        element_styles = {
            'tables': {'color': 'red', 'label': 'Table'},
            'figures': {'color': 'green', 'label': 'Figure'}
        }


Detection Processing
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def process_single_page(image_path, table_threshold=0.3, figure_threshold=0.8):
        """Process a single page to detect tables and figures"""

parameters to adjust:
- ``table_threshold``: Lower values detect more tables but may increase false positives
- ``figure_threshold``: Higher values ensure more confident figure detection
- new thresholds for more element types


Usage Examples
------------

Basic usage with default thresholds:

.. code-block:: python

    result = process_single_page("path/to/document.png")

Adjust detection sensitivity:

.. code-block:: python

    # More lenient detection
    result_lenient = process_single_page(
        "path/to/document.png",
        table_threshold=0.1,
        figure_threshold=0.6
    )

    # Stricter detection
    result_strict = process_single_page(
        "path/to/document.png",
        table_threshold=0.5,
        figure_threshold=0.9
    )

