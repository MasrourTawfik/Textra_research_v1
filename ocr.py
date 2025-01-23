import cv2
import pytesseract
import layoutparser as lp
import pdf2image
import numpy as np
from PIL import Image, ImageDraw
import json
import os
from pathlib import Path

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
custom_config = r'--psm 1'

def create_mask_for_regions(image_size, regions):
    """Create a boolean mask for regions to ignore"""
    mask = np.zeros(image_size[::-1], dtype=bool)
    
    for coords in regions:
        x1, y1, x2, y2 = [int(c) for c in coords]
        # Add some padding around the region
        x1 = max(0, x1 - 5)
        y1 = max(0, y1 - 5)
        x2 = min(image_size[0], x2 + 5)
        y2 = min(image_size[1], y2 + 5)
        mask[y1:y2, x1:x2] = True
        
    return mask

def compute_iou(box1, box2):
    """Compute Intersection over Union between two bounding boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0

def get_block_type(block):
    """Helper function to safely get block type"""
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

def process_media_block(block, image, output_folder, page_num, media_type):
    """Process a table or figure block"""
    coords = [int(c) for c in block.coordinates]
    
    # Ensure coordinates are within bounds
    coords = [
        max(0, coords[0]),
        max(0, coords[1]),
        min(image.size[0], coords[2]),
        min(image.size[1], coords[3])
    ]
    
    if coords[2] <= coords[0] or coords[3] <= coords[1]:
        return None
        
    # Save media file
    folder_name = f"{media_type}s"
    save_path = output_folder / folder_name
    save_path.mkdir(parents=True, exist_ok=True)
    filename = f"{media_type}_{page_num}.png"
    full_path = save_path / filename
    
    cropped = image.crop(coords)
    cropped.save(full_path)
    
    return {
        'block': {
            'type': media_type,
            'path': str(full_path),
            'y_position': coords[1],
            'confidence': float(block.score) if hasattr(block, 'score') else 0.8
        },
        'coords': coords,
        'file_path': str(full_path)
    }

def process_text(image, confidence_threshold=30):
    """Process text using Tesseract OCR"""
    text_data = pytesseract.image_to_data(
        image,
        config=custom_config,
        output_type=pytesseract.Output.DICT
    )
    
    text_blocks = []
    current_block = []
    current_block_y = None
    last_block_num = -1
    
    for i in range(len(text_data['text'])):
        if text_data['conf'][i] > confidence_threshold:
            block_num = text_data['block_num'][i]
            
            if block_num != last_block_num:
                if current_block:
                    text_content = ' '.join(current_block).strip()
                    if text_content:
                        text_blocks.append({
                            'type': 'text',
                            'content': text_content,
                            'y_position': current_block_y
                        })
                current_block = []
                current_block_y = text_data['top'][i]
            
            current_block.append(text_data['text'][i])
            last_block_num = block_num
    
    if current_block:
        text_content = ' '.join(current_block).strip()
        if text_content:
            text_blocks.append({
                'type': 'text',
                'content': text_content,
                'y_position': current_block_y
            })
    
    return text_blocks

def process_page(image_path, layout_model, output_folder, page_num, table_threshold=0.1, figure_threshold=0.9):
    """Process a single page focusing only on tables and figures, prioritizing tables"""
    print(f"\nProcessing page {page_num}")
    
    try:
        # Load and check image
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_array = np.array(image)
        
        # Initialize result structure
        page_result = {
            'page_num': page_num,
            'figures': [],
            'tables': [],
            'text': ''
        }
        
        # Detect layout
        print("Detecting tables and figures...")
        layout = layout_model.detect(image)
        
        # Collect and process all regions to mask FIRST
        regions_to_mask = []
        
        # Process tables first
        for block in layout:
            block_type = get_block_type(block)
            score = float(block.score) if hasattr(block, 'score') else 0.8
            
            if block_type == 'Table' and score >= table_threshold:
                coords = [int(c) for c in block.coordinates]
                regions_to_mask.append(coords)
                
                media_result = process_media_block(
                    block, 
                    image, 
                    output_folder, 
                    page_num, 
                    'table'
                )
                if media_result:
                    page_result['tables'].append(media_result)
                    
        # Then process figures
        for block in layout:
            block_type = get_block_type(block)
            score = float(block.score) if hasattr(block, 'score') else 0.8
            
            if block_type == 'Figure' and score >= figure_threshold:
                coords = [int(c) for c in block.coordinates]
                # Check if figure overlaps with any table
                is_overlapping = any(compute_iou(coords, table['coords']) > 0.3 
                                   for table in page_result['tables'])
                
                if not is_overlapping:
                    regions_to_mask.append(coords)
                    media_result = process_media_block(
                        block, 
                        image, 
                        output_folder, 
                        page_num, 
                        'figure'
                    )
                    if media_result:
                        page_result['figures'].append(media_result)
        
        # Create the mask BEFORE any text extraction
        if regions_to_mask:
            print(f"Masking {len(regions_to_mask)} regions before text extraction")
            mask = create_mask_for_regions(image.size, regions_to_mask)
            masked_image = img_array.copy()
            masked_image[mask] = 255  # White out masked regions
            masked_image = Image.fromarray(masked_image)
            
            # Extract text ONLY after masking
            page_result['text'] = pytesseract.image_to_string(
                masked_image,
                config=custom_config
            )
        else:
            # If no regions to mask, use original image
            page_result['text'] = pytesseract.image_to_string(
                image,
                config=custom_config
            )
        
        if regions_to_mask:
            print(f"Found and masked {len(page_result['tables'])} tables and {len(page_result['figures'])} figures")
        else:
            print("No tables or figures found on this page")
            
        return page_result
        
    except Exception as e:
        print(f"Error processing page {page_num}: {str(e)}")
        return None

def process_pdf(pdf_path, output_folder=None, table_threshold=0.1, figure_threshold=0.9):
    """Process PDF document"""
    if output_folder is None:
        output_folder = Path('results')
    else:
        output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Set poppler path
    os.environ['PATH'] = r"C:\Program Files\poppler\poppler-24.02.0\Library\bin" + os.pathsep + os.environ['PATH']

    # Initialize layout model
    layout_model = lp.Detectron2LayoutModel(
        'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", min(table_threshold, figure_threshold)],
        label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
    )

    result = {
        'pdf_name': Path(pdf_path).stem,
        'pages': []
    }

    try:
        # Convert PDF to images
        print("Converting PDF to images...")
        images = pdf2image.convert_from_path(pdf_path)
        
        # Process each page
        for page_num, image in enumerate(images, 1):
            # Save page image
            image_path = output_folder / f'page_{page_num}.png'
            image.save(str(image_path))
            
            # Process page
            page_result = process_page(
                image_path,
                layout_model,
                output_folder,
                page_num,
                table_threshold,
                figure_threshold
            )
            if page_result:
                result['pages'].append(page_result)

        # Save results
        with open(output_folder / 'results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None


