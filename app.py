import streamlit as st
import numpy as np
from PIL import Image
import io
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, A2, A1, A0
import colorsys
import os
import cv2

# Let's make sure the app always starts in wide mode for a better user experience
st.set_page_config(layout="wide")

class ColorReducer:
    def __init__(self, image, n_colors):
        self.image = image
        self.n_colors = n_colors
        self.colors = None
        self.labels = None
        self.reduced_image = None
        # We'll keep track of any color substitutions here (cluster_index: new_rgb)
        self.color_mapping = {}
        
    def reduce_colors(self):
        # Convert the input image to a numpy array (RGB)
        img_array = np.array(self.image)
        # If the image has an alpha channel, let's just ignore it
        if img_array.shape[-1] == 4:
            img_array = img_array[..., :3]
        # LAB color space is more perceptually uniform, so let's use that for clustering
        img_lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        # Flatten the image so each pixel is a row
        pixels_lab = img_lab.reshape(-1, 3)
        # KMeans will find the n most prominent colors in LAB space
        kmeans = KMeans(n_clusters=self.n_colors, random_state=42)
        self.labels = kmeans.fit_predict(pixels_lab)
        self.colors = kmeans.cluster_centers_
        # Assign each pixel to its cluster's color
        reduced_pixels_lab = self.colors[self.labels]
        reduced_pixels_lab = np.clip(reduced_pixels_lab, 0, 255).astype(np.uint8)
        reduced_img_lab = reduced_pixels_lab.reshape(img_lab.shape)
        # Convert back to RGB so we can display and save the image
        reduced_img_rgb = cv2.cvtColor(reduced_img_lab, cv2.COLOR_LAB2RGB)
        # If the user wants to swap out any colors, let's do that now
        if self.color_mapping:
            flat_img = reduced_img_rgb.reshape(-1, 3)
            for cluster_idx, new_color in self.color_mapping.items():
                # Replace all pixels belonging to the selected cluster
                mask = (self.labels == cluster_idx)
                flat_img[mask] = new_color
            reduced_img_rgb = flat_img.reshape(reduced_img_rgb.shape)
        self.reduced_image = reduced_img_rgb
        return Image.fromarray(np.uint8(self.reduced_image))
    
    def get_color_palette(self):
        if self.colors is None:
            return []
        # Convert the LAB cluster centers to RGB for display
        lab_colors = np.clip(self.colors, 0, 255).astype(np.uint8).reshape(-1, 1, 3)
        rgb_colors = cv2.cvtColor(lab_colors, cv2.COLOR_LAB2RGB).reshape(-1, 3)
        # Format as hex codes for easy use in the UI
        hex_colors = ['#%02x%02x%02x' % tuple(color) for color in rgb_colors]
        return hex_colors
    
    def get_palette_rgb(self):
        if self.colors is None:
            return []
        # This gives us the RGB tuples for each palette color
        lab_colors = np.clip(self.colors, 0, 255).astype(np.uint8).reshape(-1, 1, 3)
        rgb_colors = cv2.cvtColor(lab_colors, cv2.COLOR_LAB2RGB).reshape(-1, 3)
        return [tuple(color) for color in rgb_colors]
    
    def get_color_distribution(self):
        if self.labels is None:
            return []
        # Let's see how much of the image each color takes up
        unique_labels, counts = np.unique(self.labels, return_counts=True)
        total_pixels = len(self.labels)
        percentages = (counts / total_pixels) * 100
        return list(zip(self.get_color_palette(), percentages))
    
    def set_color_substitution(self, cluster_idx, new_color):
        # This will update the mapping for color substitution
        self.color_mapping[cluster_idx] = new_color
    
    def clear_color_substitutions(self):
        # Reset all color substitutions
        self.color_mapping = {}
    
    def generate_pdf(self, page_size='A4'):
        # If we haven't generated a reduced image yet, there's nothing to save
        if self.reduced_image is None:
            return None
        # Map the page size string to the actual dimensions
        page_sizes = {
            'A4': A4,
            'A3': A3,
            'A2': A2,
            'A1': A1,
            'A0': A0
        }
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=page_sizes[page_size])
        # Convert the reduced image to a PIL Image for saving
        img = Image.fromarray(np.uint8(self.reduced_image))
        # Figure out how big the image should be on the page (keep aspect ratio)
        img_width, img_height = img.size
        page_width, page_height = page_sizes[page_size]
        margin = 50  # Give it a nice margin
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin
        scale = min(max_width/img_width, max_height/img_height)
        new_width = img_width * scale
        new_height = img_height * scale
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        # Save the image temporarily so reportlab can use it
        temp_img_path = "temp_image.png"
        img.save(temp_img_path)
        # Draw the image onto the PDF
        c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
        # Add the color palette below the image for reference
        y_offset = y - 20
        for color, percentage in self.get_color_distribution():
            c.setFillColor(color)
            c.rect(x, y_offset, 20, 20, fill=1)
            c.setFillColor('black')
            c.drawString(x + 30, y_offset + 5, f"{color} ({percentage:.1f}%)")
            y_offset -= 25
        c.save()
        buffer.seek(0)
        # Clean up the temp file
        try:
            os.remove(temp_img_path)
        except:
            pass
        return buffer

def hex_to_rgb(hex_color):
    # Converts a hex string like '#ff00ff' to an (R, G, B) tuple
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def main():
    st.title("Image Color Reducer")
    # Let the user upload an image
    uploaded_file = st.file_uploader("Choose an image file", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        # Show the original and reduced images side by side
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Original Image")
            st.image(image, use_column_width=True)
        # Make the number input look nice and not too wide
        st.markdown("""
        <style>
        div[data-testid="stNumberInput"] {
            max-width: 180px;
            margin-bottom: 1rem;
        }
        div[data-testid="stNumberInput"] label {
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)
        # Let the user pick how many colors they want in the reduced image
        n_colors = st.number_input(
            "Select number of colors",
            min_value=2,
            max_value=32,
            value=8,
            step=1,
            help="Choose how many colors you want in the reduced image (2-32)"
        )
        # Create the reducer and process the image
        color_reducer = ColorReducer(image, n_colors)
        reduced_image = color_reducer.reduce_colors()
        with col2:
            st.subheader("Reduced Color Image")
            st.image(reduced_image, use_column_width=True)
        # Show the palette and how much of the image each color covers
        st.subheader("Color Palette")
        colors = color_reducer.get_color_palette()
        palette_rgb = color_reducer.get_palette_rgb()
        percentages = color_reducer.get_color_distribution()
        cols = st.columns(len(colors))
        for i, (color, percentage) in enumerate(percentages):
            with cols[i]:
                st.markdown(f"""
                <div style=\"background-color: {color}; width: 100%; height: 50px; border-radius: 5px;\"></div>
                <p style=\"text-align: center;\">{color}<br>{percentage:.1f}%</p>
                """, unsafe_allow_html=True)
        # The color substitution UI is in an expander to keep things tidy
        with st.expander("🎨 Color Substitution (Optional)"):
            st.markdown("""
            <b>Substitute a color in the reduced image:</b><br>
            1. Select a color from the palette above.<br>
            2. Choose the replacement color.<br>
            3. Click <b>Apply</b> to update the preview.<br>
            <i>Tip: You can clear all substitutions at any time.</i>
            """, unsafe_allow_html=True)
            # Give the replacement color picker more space
            sub_col1, sub_col2, sub_col3 = st.columns([2, 4, 2])
            with sub_col1:
                # Only allow picking from the palette for the color to replace
                old_color = st.selectbox("Color to replace", options=colors, key="old_color_select")
            with sub_col2:
                # Let the user pick any color as the replacement
                new_color = st.color_picker("Replacement color", "#000000", key="new_color")
                # Show the hex code for clarity
                st.markdown(f"<div style='margin-top: 8px; font-size: 14px;'><b>Hex:</b> {new_color}</div>", unsafe_allow_html=True)
            with sub_col3:
                st.write("")
                apply = st.button("Apply", key="apply_subst")
                clear = st.button("Clear All", key="clear_subst")
            if apply:
                # Figure out which cluster index matches the selected palette color
                try:
                    cluster_idx = colors.index(old_color)
                except ValueError:
                    st.warning("Selected color is not in the palette. Please copy the hex code from above.")
                    cluster_idx = None
                if cluster_idx is not None:
                    new_rgb = hex_to_rgb(new_color)
                    color_reducer.set_color_substitution(cluster_idx, new_rgb)
                    st.rerun()
            if clear:
                color_reducer.clear_color_substitutions()
                st.rerun()
        # PDF export section
        st.subheader("Generate PDF")
        page_size = st.selectbox("Select page size", ['A4', 'A3', 'A2', 'A1', 'A0'])
        if st.button("Generate PDF"):
            pdf_buffer = color_reducer.generate_pdf(page_size)
            if pdf_buffer:
                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name="reduced_color_image.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main()
