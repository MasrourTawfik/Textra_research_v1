# Textra_research_v1
An intelligent system for analyzing and synthesizing Reinforcement Learning research papers. 

Documentation available at: `Textra Documentation <https://textra-research-v1.readthedocs.io/en/latest/index.html>`_

## Prerequisites

- Python 3.8 or higher
- CUDA 12.4 compatible GPU
- NVIDIA drivers installed
- Git

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install PyTorch and related packages:
```bash
pip install torch==2.4.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

3. Install Detectron2:
```bash
git clone https://github.com/facebookresearch/detectron2.git
python -m pip install -e detectron2
```

## Requirements

Install all required packages using:
```bash
pip install -r requirements.txt
```

## Usage

1. Clone this repository
2. Create a virtual environment
3. Install requirements:
```bash
pip install -r requirements.txt
```

## Common Issues

1. CUDA version mismatch:
   - Ensure your NVIDIA drivers support CUDA 12.4
   - Check GPU compatibility

2. Detectron2 installation issues:
   - Make sure you have Microsoft Visual C++ Build Tools installed (Windows)
   - Check that you have sufficient disk space
   - Ensure all prerequisites are properly installed
