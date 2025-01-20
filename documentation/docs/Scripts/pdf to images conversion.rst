PDF to Image Conversion
========================

Requirements
-------------
Before running the conversion script, ensure you have:

1. pdf2image library:

   .. code-block:: bash

      pip install pdf2image

2. Poppler for Windows:
   
   - Download from: https://github.com/oschwartz10612/poppler-windows/releases/
   - Extract to a known location (e.g., ``C:\Program Files\poppler``)
   - Add bin directory to PATH or specify directly in the code

Implementation
---------------
The conversion process uses pdf2image to convert PDF files to high-quality PNG images:

.. code-block:: python

    import os
    from pdf2image import convert_from_path
    from pathlib import Path

    def convert_pdfs_to_images(pdf_dir, output_base_dir, poppler_path, dpi=300):
        # Verify paths
        print(f"Poppler path: {poppler_path}")
        print(f"PDF directory: {pdf_dir}")
        print(f"Output directory: {output_base_dir}")
        if not os.path.exists(poppler_path):
            raise Exception(f"Poppler path does not exist: {poppler_path}")
        
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_file in pdf_files:
            pdf_name = os.path.splitext(pdf_file)[0]
            output_dir = os.path.join(output_base_dir, pdf_name)
            Path(output_dir).mkdir(exist_ok=True)
            
            pdf_path = os.path.join(pdf_dir, pdf_file)
            try:
                print(f"Processing {pdf_file}...")
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    poppler_path=poppler_path
                )
                
                for i, image in enumerate(images):
                    image_path = os.path.join(output_dir, f'page_{i+1}.png')
                    image.save(image_path, 'PNG')
                    print(f'Saved {image_path}')
                    
            except Exception as e:
                print(f'Error processing {pdf_file}: {str(e)}')
Parameters
~~~~~~~~~~~
- ``pdf_dir``: Directory containing PDF files
- ``output_base_dir``: Base directory for output images
- ``poppler_path``: Path to Poppler binaries
- ``dpi``: Resolution of output images (default: 300)

Directory Structure
-------------------

Input structure:

.. code-block:: none

    data/
    └── raw/
        └── pdfs/
            ├── article1.pdf
            ├── article2.pdf
            └── ...

Output structure:

.. code-block:: none

    data/
    └── processed/
        └── pdf_images/
            ├── article1/
            │   ├── page_1.png
            │   ├── page_2.png
            │   └── ...
            ├── article2/
            │   ├── page_1.png
            │   ├── page_2.png
            │   └── ...
            └── ...

Usage
-----

Configure paths and run the conversion:

.. code-block:: python

    # Configure paths
    pdf_dir = "path/to/pdf/directory"
    output_dir = "path/to/output/directory"
    poppler_path = "path/to/poppler/bin"

    # Run conversion
    convert_pdfs_to_images(pdf_dir, output_dir, poppler_path)

