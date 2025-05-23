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
        # Ensure the image is in RGB mode
        if self.image.mode != "RGB":
            self.image = self.image.convert("RGB")
            print("Converted image to RGB mode")

        # Convert the input image to a numpy array (RGB)
        img_array = np.array(self.image)
        print(f"Input image shape: {img_array.shape}, dtype: {img_array.dtype}")
        print(f"Input image pixel range: {img_array.min()} to {img_array.max()}")

        # If the image is grayscale (single channel), convert it to RGB
        if len(img_array.shape) == 2 or img_array.shape[-1] == 1:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            print("Converted grayscale image to RGB")

        # If the image has an alpha channel, let's just ignore it
        if img_array.shape[-1] == 4:
            img_array = img_array[..., :3]
            print("Removed alpha channel from image")

        # Ensure the image is in the correct format
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)

        # LAB color space is more perceptually uniform, so let's use that for clustering
        img_lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        print(f"LAB values range: {img_lab.min()} to {img_lab.max()}")

        # Flatten the image so each pixel is a row
        pixels_lab = img_lab.reshape(-1, 3)

        # KMeans will find the n most prominent colors in LAB space
        kmeans = KMeans(n_clusters=self.n_colors, init='k-means++', random_state=42)
        self.labels = kmeans.fit_predict(pixels_lab)
        self.colors = kmeans.cluster_centers_
        print(f"KMeans cluster centers (LAB): {self.colors}")
        print(f"KMeans labels: {np.unique(self.labels)}")

        # Assign each pixel to its cluster's color
        reduced_pixels_lab = self.colors[self.labels]
        reduced_pixels_lab = np.clip(reduced_pixels_lab, 0, 255).astype(np.uint8)
        print(f"Reduced LAB values range: {reduced_pixels_lab.min()} to {reduced_pixels_lab.max()}")

        reduced_img_lab = reduced_pixels_lab.reshape(img_lab.shape)

        # Convert back to RGB so we can display and save the image
        reduced_img_rgb = cv2.cvtColor(reduced_img_lab, cv2.COLOR_LAB2RGB)
        print(f"Reduced RGB values range: {reduced_img_rgb.min()} to {reduced_img_rgb.max()}")

        # Apply color substitution using the replace_color logic
        if self.color_mapping:
            reduced_img_rgb = self.apply_color_substitution(reduced_img_rgb)

        self.reduced_image = reduced_img_rgb
        return Image.fromarray(np.uint8(self.reduced_image))

    def apply_color_substitution(self, image_array):
        """
        Applies color substitution to the reduced image using the replace_color logic.

        Args:
            image_array (numpy.ndarray): The reduced image as a NumPy array.

        Returns:
            numpy.ndarray: The modified image with color substitutions applied.
        """
        substitutor = ColorSubstitutor()
        for cluster_idx, new_color in self.color_mapping.items():
            old_color = tuple(map(int, self.colors[cluster_idx]))  # Convert LAB cluster center to RGB
            image_array = substitutor.apply(image_array, old_color, new_color)
        return image_array
    
    def get_color_palette(self):
        if self.colors is None:
            return []
        # Convert the LAB cluster centers to RGB for display
        lab_colors = np.clip(self.colors, 0, 255).astype(np.uint8).reshape(-1, 1, 3)
        rgb_colors = cv2.cvtColor(lab_colors, cv2.COLOR_LAB2RGB).reshape(-1, 3)

        # Apply substitutions from color_mapping
        for cluster_idx, new_color in self.color_mapping.items():
            rgb_colors[cluster_idx] = new_color

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

        # Get the updated palette with substitutions applied
        lab_colors = np.clip(self.colors, 0, 255).astype(np.uint8).reshape(-1, 1, 3)
        rgb_colors = cv2.cvtColor(lab_colors, cv2.COLOR_LAB2RGB).reshape(-1, 3)

        # Apply substitutions from color_mapping
        for cluster_idx, new_color in self.color_mapping.items():
            rgb_colors[cluster_idx] = new_color

        # Format as hex codes for easy use in the UI
        hex_colors = ['#%02x%02x%02x' % tuple(color) for color in rgb_colors]

        # Return the updated color distribution
        return list(zip(hex_colors, percentages))
    
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
        margin = 10  # Give it a nice margin
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin
        scale = min(max_width/img_width, max_height/img_height)
        new_width = img_width * scale
        new_height = img_height * scale
        x = (page_width - new_width) / 2
        y = page_height - new_height - margin
        # Save the image temporarily so reportlab can use it
        temp_img_path = "temp_image.png"
        img.save(temp_img_path)
        # Draw the image onto the PDF
        c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
        # Add the color palette in a grid format below the image
        y_offset = y - 30  # Start below the image
        grid_cols = 8  # Number of columns in the grid
        cell_size = 25  # Size of each color cell
        padding = 40  # Padding between cells
        updated_distribution = self.get_color_distribution()  # Get updated palette and percentages
        for i, (color, percentage) in enumerate(updated_distribution):
            col = i % grid_cols
            row = i // grid_cols
            cell_x = margin + col * (cell_size + padding)
            cell_y = y_offset - row * (cell_size + padding)
            if cell_y < margin:  # If we run out of space, start a new page
                c.showPage()
                y_offset = page_height - margin
                cell_y = y_offset - row * (cell_size + padding)
            # Draw the color cell
            c.setFillColorRGB(
                int(color[1:3], 16) / 255.0,
                int(color[3:5], 16) / 255.0,
                int(color[5:7], 16) / 255.0
            )  # Convert hex to RGB for ReportLab
            c.rect(cell_x, cell_y, cell_size, cell_size, fill=1)
            # Add the color hex code and percentage below the cell
            c.setFillColor('black')
            c.setFont("Helvetica", 8)
            c.drawString(cell_x, cell_y - 10, f"{color} ({percentage:.1f}%)")
        c.save()
        buffer.seek(0)
        # Clean up the temp file
        try:
            os.remove(temp_img_path)
        except:
            pass
        return buffer

    def generate_substituted_pdf(self, page_size='A4', substituted_image=None):
        """
        Generates a PDF with the substituted image and color palette details.

        Args:
            page_size (str): The page size for the PDF (default is 'A4').
            substituted_image (PIL.Image.Image): The substituted image to include in the PDF.

        Returns:
            io.BytesIO: A buffer containing the PDF data.
        """
        if substituted_image is None:
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

        # Convert the substituted image to a PIL Image for saving
        img = substituted_image
        img_width, img_height = img.size
        page_width, page_height = page_sizes[page_size]
        margin = 50  # Give it a nice margin
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin
        scale = min(max_width / img_width, max_height / img_height)
        new_width = img_width * scale
        new_height = img_height * scale
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2

        # Save the image temporarily so reportlab can use it
        temp_img_path = "temp_substituted_image.png"
        img.save(temp_img_path)
        c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)

        # Add the updated color palette below the image for reference
        y_offset = y - 20
        updated_distribution = self.get_color_distribution()  # Get updated palette and percentages
        for color, percentage in updated_distribution:
            c.setFillColorRGB(
                int(color[1:3], 16) / 255.0,
                int(color[3:5], 16) / 255.0,
                int(color[5:7], 16) / 255.0
            )  # Convert hex to RGB for ReportLab
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

class ColorSubstitutor:
    def __init__(self, tolerance=20):
        """
        Initializes the ColorSubstitutor with a tolerance level.

        Args:
            tolerance (int): The tolerance level for color matching (default is 20).
        """
        self.tolerance = tolerance

    def apply(self, image_array, old_color, new_color):
        """
        Applies color substitution to an image array.

        Args:
            image_array (numpy.ndarray): The image as a NumPy array (RGB format).
            old_color (tuple): The RGB color to replace (e.g., (255, 0, 0)).
            new_color (tuple): The RGB replacement color (e.g., (0, 255, 0)).

        Returns:
            numpy.ndarray: The modified image with the color substitution applied.
        """
        img = Image.fromarray(image_array)
        img = img.convert("RGBA")
        data = img.getdata()

        new_data = []
        for pixel in data:
            r, g, b, a = pixel
            distance = ((r - old_color[0]) ** 2 + (g - old_color[1]) ** 2 + (b - old_color[2]) ** 2) ** 0.5
            if distance <= self.tolerance:
                new_data.append(new_color + (a,))
            else:
                new_data.append(pixel)

        img.putdata(new_data)
        return np.array(img.convert("RGB"))

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
            st.image(image, use_container_width=True)
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
            st.image(reduced_image, use_container_width=True)
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
                # Convert the selected hex color to RGB
                old_rgb = hex_to_rgb(old_color)
                new_rgb = hex_to_rgb(new_color)

                # Use the ColorSubstitutor to apply the substitution
                substitutor = ColorSubstitutor(tolerance=20)  # You can adjust the tolerance as needed
                reduced_image_array = np.array(reduced_image)  # Convert PIL Image to NumPy array
                modified_image_array = substitutor.apply(reduced_image_array, old_rgb, new_rgb)

                # Convert the modified image back to a PIL Image and store it in session state
                st.session_state["modified_image"] = Image.fromarray(modified_image_array)
                st.image(st.session_state["modified_image"], use_container_width=True)  # Update the displayed image

                # Update the color mapping in the reducer
                cluster_idx = palette_rgb.index(old_rgb)  # Find the cluster index for the old color
                color_reducer.set_color_substitution(cluster_idx, new_rgb)

                # Display the updated color palette and percentages
                st.subheader("Updated Color Palette and Percentages")
                updated_percentages = color_reducer.get_color_distribution()
                cols = st.columns(len(updated_percentages))
                for i, (color, percentage) in enumerate(updated_percentages):
                    with cols[i]:
                        st.markdown(f"""
                        <div style=\"background-color: {color}; width: 100%; height: 50px; border-radius: 5px;\"></div>
                        <p style=\"text-align: center;\">{color}<br>{percentage:.1f}%</p>
                        """, unsafe_allow_html=True)
            if clear:
                color_reducer.clear_color_substitutions()
                # Reprocess the reduced image without substitutions
                reduced_image = color_reducer.reduce_colors()
                st.session_state.pop("modified_image", None)  # Remove the substituted image from session state
                st.image(reduced_image, use_container_width=True)  # Update the displayed image
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
