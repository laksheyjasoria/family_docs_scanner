import cv2
import numpy as np
from PIL import Image

class ImageProcessor:
    @staticmethod
    def detect_document_rect(pil_image, margin=10):
        """
        Detect the main document/card in the image.
        Works on complex backgrounds like bedsheets, patterned surfaces.
        Returns (x, y, w, h) or None.
        """
        try:
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to OpenCV format
            cv_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
            
            # Sharpening filter to enhance edges
            kernel_sharpen = np.array([[-1,-1,-1],
                                       [-1, 9,-1],
                                       [-1,-1,-1]])
            sharpened = cv2.filter2D(blurred, -1, kernel_sharpen)
            
            best_rect = None
            best_score = 0
            
            # Strategy 1: Adaptive Threshold + Contour approximation
            thresh1 = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY_INV, 25, 15)
            # Morphological closing to close gaps
            kernel = np.ones((5,5), np.uint8)
            thresh1 = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours1, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours1:
                area = cv2.contourArea(cnt)
                img_area = gray.shape[0] * gray.shape[1]
                # Filter by area: between 5% and 90% of image
                if 0.05 < area/img_area < 0.95:
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                    # Check if contour is roughly rectangular (4-8 vertices)
                    if 4 <= len(approx) <= 8:
                        x, y, w, h = cv2.boundingRect(cnt)
                        aspect_ratio = w / h if h > 0 else 0
                        # Typical document aspect ratio between 0.5 and 2.0
                        if 0.5 < aspect_ratio < 2.0:
                            rect_area = w * h
                            contour_area_ratio = area / rect_area if rect_area > 0 else 0
                            # Score: area ratio (how well it fills the bounding box)
                            score = contour_area_ratio
                            if score > best_score:
                                best_score = score
                                best_rect = (x, y, w, h)
            
            # Strategy 2: Canny edge detection with dilation
            if best_rect is None:
                edges = cv2.Canny(sharpened, 30, 100)
                kernel = np.ones((5,5), np.uint8)
                dilated = cv2.dilate(edges, kernel, iterations=3)
                contours2, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for cnt in contours2:
                    area = cv2.contourArea(cnt)
                    img_area = gray.shape[0] * gray.shape[1]
                    if 0.05 < area/img_area < 0.95:
                        x, y, w, h = cv2.boundingRect(cnt)
                        aspect_ratio = w / h if h > 0 else 0
                        if 0.3 < aspect_ratio < 3.0:
                            rect_area = w * h
                            contour_area_ratio = area / rect_area if rect_area > 0 else 0
                            score = contour_area_ratio
                            if score > best_score:
                                best_score = score
                                best_rect = (x, y, w, h)
            
            # Strategy 3: Simple threshold (Otsu)
            if best_rect is None:
                _, thresh3 = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # Invert if needed (dark object on light background)
                if np.mean(thresh3) > 127:
                    thresh3 = cv2.bitwise_not(thresh3)
                thresh3 = cv2.morphologyEx(thresh3, cv2.MORPH_CLOSE, kernel, iterations=2)
                contours3, _ = cv2.findContours(thresh3, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for cnt in contours3:
                    area = cv2.contourArea(cnt)
                    img_area = gray.shape[0] * gray.shape[1]
                    if 0.05 < area/img_area < 0.95:
                        x, y, w, h = cv2.boundingRect(cnt)
                        aspect_ratio = w / h if h > 0 else 0
                        if 0.3 < aspect_ratio < 3.0:
                            rect_area = w * h
                            contour_area_ratio = area / rect_area if rect_area > 0 else 0
                            score = contour_area_ratio
                            if score > best_score:
                                best_score = score
                                best_rect = (x, y, w, h)
            
            # Apply margin if we found a rectangle
            if best_rect:
                x, y, w, h = best_rect
                # Add margin
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(pil_image.width - x, w + 2*margin)
                h = min(pil_image.height - y, h + 2*margin)
                
                # Final sanity check: rectangle should be at least 50x50 pixels
                if w > 50 and h > 50:
                    return (int(x), int(y), int(w), int(h))
            
            return None
            
        except Exception as e:
            print(f"Detection error: {e}")
            return None

    @staticmethod
    def auto_crop(pil_image, margin=10):
        """Auto-crop and return the cropped image"""
        rect = ImageProcessor.detect_document_rect(pil_image, margin)
        if rect:
            x, y, w, h = rect
            return pil_image.crop((x, y, x+w, y+h))
        return pil_image

    @staticmethod
    def resize_to_dpi(pil_image, target_dpi, original_dpi=300):
        scale = target_dpi / original_dpi
        new_size = (int(pil_image.width * scale), int(pil_image.height * scale))
        return pil_image.resize(new_size, Image.Resampling.LANCZOS)