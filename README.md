# ReduceColor: Streamlit Image Color Reducer

A user-friendly Streamlit app to reduce the number of colors in an image, preview the result, and export a printable PDF. Perfect for artists, designers, crafters, and anyone who wants to simplify or stylize images for printing, painting, or digital use.

## Features
- **Upload any image** (PNG, JPG, JPEG)
- **Reduce colors**: Choose how many colors you want in the output (2–32)
- **Side-by-side comparison**: Instantly see the original and reduced-color images
- **Color palette extraction**: View the hex codes and usage percentages of the most prominent colors
- **Color substitution**: Easily swap any palette color for a custom one, with live preview
- **Export to PDF**: Download a printable PDF with the reduced image and its color palette, in sizes from A4 to A0
- **Modern, clean UI**: Designed for clarity and ease of use

## Installation
1. **Clone this repository**
   ```bash
   git clone [<your-repo-url>](https://github.com/0NE-C0DEMAN/ReduceColor)
   cd ReduceColor
   ```
2. **(Recommended) Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. **Start the Streamlit app**
   ```bash
   streamlit run app.py
   ```
2. **Open your browser** to the local URL shown (usually http://localhost:8501)
3. **Upload an image** and experiment with color reduction, palette editing, and PDF export!

## How it Works
- Uses KMeans clustering in LAB color space for perceptually accurate color reduction
- Lets you substitute palette colors by cluster, so replacements are always accurate
- PDF export uses ReportLab for high-quality, print-ready output

## Example Use Cases
- Create paint-by-number templates
- Prepare images for screen printing, embroidery, or vinyl cutting
- Stylize photos for digital art or posters
- Extract color palettes for design inspiration

## Requirements
- Python 3.8+
- See `requirements.txt` for all dependencies

---
