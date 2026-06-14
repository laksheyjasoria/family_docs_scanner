import uuid
import shutil
from pathlib import Path
from PIL import Image
import io
from core.image_processor import ImageProcessor

class SessionManager:
    def __init__(self):
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        self.session_id = str(uuid.uuid4())[:8]
        self.session_path = self.temp_dir / self.session_id
        self.session_path.mkdir(exist_ok=True)
        self.pages = []  # list of (original_path, edited_path)
        self.saved_flag = False

    def _image_to_bytes(self, image):
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    def _bytes_to_image(self, bytes_data):
        return Image.open(io.BytesIO(bytes_data))

    def add_page(self, pil_image, auto_crop=False, auto_deskew=False, margin=10):
        edited = pil_image.copy()
        if auto_deskew:
            edited = ImageProcessor.deskew(edited)
        if auto_crop:
            edited = ImageProcessor.auto_crop(edited, margin)

        orig_bytes = self._image_to_bytes(pil_image)
        edited_bytes = self._image_to_bytes(edited)

        idx = len(self.pages)
        orig_path = self.session_path / f"page_{idx}_original.png"
        edited_path = self.session_path / f"page_{idx}_edited.png"
        pil_image.save(orig_path)
        edited.save(edited_path)

        self.pages.append((orig_bytes, edited_bytes))
        self.saved_flag = False

    def delete_page(self, idx):
        if idx < 0 or idx >= len(self.pages):
            return
        # Delete disk files
        orig_path = self.session_path / f"page_{idx}_original.png"
        edited_path = self.session_path / f"page_{idx}_edited.png"
        try:
            if orig_path.exists():
                orig_path.unlink()
            if edited_path.exists():
                edited_path.unlink()
        except:
            pass
        self.pages.pop(idx)
        # Renumber remaining files
        for i in range(idx, len(self.pages)):
            old_orig = self.session_path / f"page_{i+1}_original.png"
            old_edited = self.session_path / f"page_{i+1}_edited.png"
            new_orig = self.session_path / f"page_{i}_original.png"
            new_edited = self.session_path / f"page_{i}_edited.png"
            try:
                if old_orig.exists():
                    old_orig.rename(new_orig)
                if old_edited.exists():
                    old_edited.rename(new_edited)
            except:
                pass
        self.saved_flag = False

    def move_page(self, from_idx, to_idx):
        if from_idx < 0 or from_idx >= len(self.pages) or to_idx < 0 or to_idx >= len(self.pages):
            return
        if from_idx == to_idx:
            return
        self.pages.insert(to_idx, self.pages.pop(from_idx))
        # Rename disk files to reflect new order
        for i in range(len(self.pages)):
            orig_bytes, edited_bytes = self.pages[i]
            orig_path = self.session_path / f"page_{i}_original.png"
            edited_path = self.session_path / f"page_{i}_edited.png"
            self._bytes_to_image(orig_bytes).save(orig_path)
            self._bytes_to_image(edited_bytes).save(edited_path)
        self.saved_flag = False

    def get_page_edited(self, idx):
        if idx < 0 or idx >= len(self.pages):
            return None
        return self._bytes_to_image(self.pages[idx][1])

    def get_page_original(self, idx):
        if idx < 0 or idx >= len(self.pages):
            return None
        return self._bytes_to_image(self.pages[idx][0])

    def get_all_pages(self, use_edited=True):
        images = []
        for orig_bytes, edited_bytes in self.pages:
            if use_edited:
                images.append(self._bytes_to_image(edited_bytes))
            else:
                images.append(self._bytes_to_image(orig_bytes))
        return images

    def edit_page(self, idx, new_image):
        if idx < 0 or idx >= len(self.pages):
            return
        orig_bytes = self.pages[idx][0]
        edited_bytes = self._image_to_bytes(new_image)
        self.pages[idx] = (orig_bytes, edited_bytes)
        # Update disk file
        edited_path = self.session_path / f"page_{idx}_edited.png"
        new_image.save(edited_path)
        self.saved_flag = False

    def replace_original(self, idx, new_image):
        """Replace the original image for a page (used after cropping)"""
        if idx < 0 or idx >= len(self.pages):
            return
        orig_bytes = self._image_to_bytes(new_image)
        edited_bytes = self._image_to_bytes(new_image)
        self.pages[idx] = (orig_bytes, edited_bytes)
        orig_path = self.session_path / f"page_{idx}_original.png"
        edited_path = self.session_path / f"page_{idx}_edited.png"
        new_image.save(orig_path)
        new_image.save(edited_path)
        self.saved_flag = False

    def reset_page(self, idx, auto_crop=False, auto_deskew=False, margin=10):
        if idx < 0 or idx >= len(self.pages):
            return
        original = self._bytes_to_image(self.pages[idx][0])
        edited = original.copy()
        if auto_deskew:
            edited = ImageProcessor.deskew(edited)
        if auto_crop:
            edited = ImageProcessor.auto_crop(edited, margin)
        edited_bytes = self._image_to_bytes(edited)
        self.pages[idx] = (self.pages[idx][0], edited_bytes)
        edited_path = self.session_path / f"page_{idx}_edited.png"
        edited.save(edited_path)
        self.saved_flag = False

    def page_count(self):
        return len(self.pages)

    def has_unsaved_changes(self):
        return not self.saved_flag and self.page_count() > 0

    def mark_saved(self):
        self.saved_flag = True

    def clear_session(self):
        # Delete session folder
        if self.session_path.exists():
            try:
                shutil.rmtree(self.session_path)
            except:
                pass
        # Create new session
        self.session_id = str(uuid.uuid4())[:8]
        self.session_path = self.temp_dir / self.session_id
        self.session_path.mkdir(exist_ok=True)
        self.pages = []
        self.saved_flag = False