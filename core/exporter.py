from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import re

class Exporter:
    def __init__(self, settings):
        self.settings = settings
    
    def _clean_path(self, path_str):
        """Remove duplicate concatenation in export folder path"""
        pattern = r'(.+?FamilyDocs)(.+?FamilyDocs)'
        match = re.match(pattern, path_str, re.IGNORECASE)
        if match:
            return match.group(1)
        return path_str
    
    def export_session(self, session_manager, family_member, doc_type):
        raw_path = self.settings.get("export_folder", "")
        raw_path = self._clean_path(raw_path)
        base_dir = Path(raw_path).resolve()
        
        member_dir = base_dir / family_member
        doc_dir = member_dir / doc_type
        orig_dir = doc_dir / "original"
        dpi150_dir = doc_dir / "150dpi"
        dpi300_dir = doc_dir / "300dpi"
        pdf_dir = doc_dir / "pdf"
        
        for d in [orig_dir, dpi150_dir, dpi300_dir, pdf_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        pages = session_manager.get_all_pages(use_edited=True)
        pdf_images = []
        
        for idx, img in enumerate(pages):
            orig_path = orig_dir / f"page_{idx+1}.png"
            img.save(orig_path)
            
            if 150 in self.settings.get("dpi_versions", []):
                dpi150_path = dpi150_dir / f"page_{idx+1}.jpg"
                img.save(dpi150_path, "JPEG", quality=85)
            
            if 300 in self.settings.get("dpi_versions", []):
                dpi300_path = dpi300_dir / f"page_{idx+1}.jpg"
                img.save(dpi300_path, "JPEG", quality=95)
            
            pdf_images.append(img)
        
        if self.settings.get("create_pdf", True):
            pdf_path = pdf_dir / f"{family_member}_{doc_type}.pdf"
            self._create_pdf(pdf_images, pdf_path)
        
        return doc_dir
    
    def _create_pdf(self, images, output_path):
        if not images:
            return
        first = images[0]
        width, height = first.size
        c = canvas.Canvas(str(output_path), pagesize=(width, height))
        for img in images:
            c.drawImage(ImageReader(img), 0, 0, width, height)
            c.showPage()
        c.save()