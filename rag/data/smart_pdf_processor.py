#!/usr/bin/env python3
"""
smart_pdf_processor.py - Version adaptée pour le pipeline RAG
Extraction intelligente des PDF avec OCR, tableaux et images
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re as _re

import fitz
import pdfplumber
import pytesseract
from PIL import Image
import requests
import base64

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    from spellchecker import SpellChecker
    _SPELL_FR = SpellChecker(language="fr")
    SPELLCHECK_AVAILABLE = True
except ImportError:
    SPELLCHECK_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("smart_pdf")

# Configuration
MIN_CHARS_FOR_TEXT_PAGE = 40
OCR_RENDER_DPI = 300
MIN_IMAGE_SIZE_PX = 80
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")


@dataclass
class PageResult:
    page_number: int
    method_used: str
    text: str = ""
    tables_markdown: list = field(default_factory=list)
    images_extracted: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def describe_image_with_vision_llm(image_path: str, use_vision_llm: bool = True) -> str:
    """Description d'image via API NVIDIA NIM (optionnelle)"""
    if not use_vision_llm or not NVIDIA_API_KEY:
        return f"[Image: {os.path.basename(image_path)}]"
    
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                        },
                        {
                            "type": "text",
                            "text": "Décris cette image technique en français, de manière concise pour indexation dans un moteur de recherche. Mentionne les éléments clés visibles."
                        }
                    ]
                }
            ],
            "model": "meta/llama-3.2-90b-vision-instruct",
            "max_tokens": 256,
            "temperature": 0.2,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stream": False
        }
        
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"[Image: {os.path.basename(image_path)}]"
            
    except Exception as e:
        log.warning(f"Échec description image: {e}")
        return f"[Image: {os.path.basename(image_path)}]"


def is_scanned_page(page: fitz.Page) -> bool:
    text = page.get_text("text").strip()
    return len(text) < MIN_CHARS_FOR_TEXT_PAGE


def _valid_french_word_ratio(text: str, min_words: int = 10) -> float:
    if not SPELLCHECK_AVAILABLE:
        return -1
    words = _re.findall(r"[a-zàâäéèêëïîôöùûüçñ]{4,}", text.lower())
    if len(words) < min_words:
        return -1
    valid = _SPELL_FR.known(words)
    return len(valid) / len(words) if words else -1


def is_text_garbled(text: str, min_valid_ratio: float = 0.35, min_words: int = 10) -> bool:
    ratio = _valid_french_word_ratio(text, min_words)
    if ratio < 0:
        return False
    return ratio < min_valid_ratio


def _auto_orient_image(img: Image.Image, lang: str) -> Image.Image:
    try:
        osd = pytesseract.image_to_osd(img)
        angle_match = _re.search(r"Rotate:\s*(\d+)", osd)
        conf_match = _re.search(r"Orientation confidence:\s*([\d.]+)", osd)
        angle = int(angle_match.group(1)) if angle_match else 0
        confidence = float(conf_match.group(1)) if conf_match else 0.0
        if angle in (90, 180, 270) and confidence >= 1.0:
            return img.rotate(-angle, expand=True)
        return img
    except Exception:
        pass

    if not SPELLCHECK_AVAILABLE:
        return img

    best_img, best_score = img, -1.0
    for angle in (0, 90, 180, 270):
        candidate = img.rotate(angle, expand=True) if angle else img
        try:
            sample = pytesseract.image_to_string(candidate, lang=lang)
        except Exception:
            continue
        score = _valid_french_word_ratio(sample, min_words=5)
        if score > best_score:
            best_score, best_img = score, candidate
    return best_img


def ocr_page(page: fitz.Page, lang: str = "fra+ara") -> str:
    mat = fitz.Matrix(OCR_RENDER_DPI / 72, OCR_RENDER_DPI / 72)
    pix = page.get_pixmap(matrix=mat)
    img_path = f"/tmp/_ocr_page_{page.number}.png"
    pix.save(img_path)
    try:
        img = Image.open(img_path)
        img = _auto_orient_image(img, lang)
        text = pytesseract.image_to_string(img, lang=lang)
    except pytesseract.TesseractError as e:
        log.warning(f"Langue OCR '{lang}' indisponible ({e}), repli sur 'eng'")
        text = pytesseract.image_to_string(Image.open(img_path), lang="eng")
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)
    return text.strip()


def extract_tables_pdfplumber(pdf_path: str, page_number: int) -> list:
    tables_md = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_number]
            raw_tables = page.extract_tables()
            for t in raw_tables:
                if t and len(t) > 0:
                    tables_md.append(table_to_markdown(t))
    except Exception as e:
        log.debug(f"pdfplumber a échoué page {page_number + 1}: {e}")
    return tables_md


def extract_tables_camelot(pdf_path: str, page_number: int) -> list:
    tables_md = []
    try:
        tables = camelot.read_pdf(pdf_path, pages=str(page_number + 1), flavor="lattice")
        if tables.n == 0:
            tables = camelot.read_pdf(pdf_path, pages=str(page_number + 1), flavor="stream")
        for t in tables:
            tables_md.append(t.df.to_markdown(index=False))
    except Exception as e:
        log.debug(f"camelot a échoué page {page_number + 1}: {e}")
    return tables_md


def table_to_markdown(table: list) -> str:
    if not table or not table[0]:
        return ""
    clean = [[(cell or "").strip().replace("\n", " ") for cell in row] for row in table]
    header = clean[0]
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for row in clean[1:]:
        row = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def is_likely_fake_table(table_md: str) -> bool:
    lines = [l for l in table_md.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return True
    header_cols = [c for c in lines[0].split("|") if c.strip()]
    return len(header_cols) < 2


def process_pdf_smart(pdf_path: str, ocr_lang: str = "fra+ara", 
                      use_vision_llm: bool = True, 
                      output_dir: str = None) -> List[Dict[str, Any]]:
    """
    Traite un PDF intelligemment et retourne les chunks pour le RAG
    
    Args:
        pdf_path: Chemin du PDF
        ocr_lang: Langues pour l'OCR
        use_vision_llm: Activer la description des images
        output_dir: Dossier de sortie pour les images (optionnel)
    
    Returns:
        Liste de chunks avec métadonnées
    """
    doc_name = Path(pdf_path).stem
    doc = fitz.open(pdf_path)
    
    all_chunks = []
    current_page = 1
    
    for page_number in range(len(doc)):
        page = doc[page_number]
        page_result = process_page(
            doc, page, pdf_path, page_number, 
            output_dir, doc_name, ocr_lang, use_vision_llm
        )
        
        # Construire le contenu de la page
        content_parts = []
        
        if page_result.text:
            content_parts.append(page_result.text)
        
        for table_md in page_result.tables_markdown:
            content_parts.append(f"\n**Tableau:**\n{table_md}")
        
        for img in page_result.images_extracted:
            content_parts.append(f"\n**Figure:** {img['description']}")
        
        if content_parts:
            chunk = {
                "page_content": "\n".join(content_parts),
                "metadata": {
                    "page_number": page_result.page_number,
                    "source_file": doc_name + ".pdf",
                    "source_path": pdf_path,
                    "format": "pdf",
                    "method": page_result.method_used,
                    "warnings": page_result.warnings
                }
            }
            all_chunks.append(chunk)
    
    doc.close()
    return all_chunks


def process_page(doc: fitz.Document, page: fitz.Page, pdf_path: str, page_number: int,
                 output_dir: str, doc_name: str, ocr_lang: str, use_vision_llm: bool) -> PageResult:
    result = PageResult(page_number=page_number + 1, method_used="")
    
    # 1) Détection scan / texte corrompu
    native_text = page.get_text("text").strip()
    needs_ocr = is_scanned_page(page)
    corrupted = False
    
    if not needs_ocr and is_text_garbled(native_text):
        needs_ocr = True
        corrupted = True
    
    # 2) OCR si nécessaire
    if needs_ocr:
        result.method_used = "ocr"
        if corrupted:
            result.warnings.append("Texte corrompu -> OCR")
        try:
            result.text = ocr_page(page, lang=ocr_lang)
        except Exception as e:
            result.warnings.append(f"Échec OCR: {e}")
    else:
        result.method_used = "texte_natif"
        result.text = native_text
    
    # 3) Extraction des tableaux (uniquement pour texte natif)
    if result.method_used == "texte_natif":
        try:
            raw_tables = []
            if CAMELOT_AVAILABLE:
                raw_tables = extract_tables_camelot(pdf_path, page_number)
            if not raw_tables:
                raw_tables = extract_tables_pdfplumber(pdf_path, page_number)
            raw_tables = [t for t in raw_tables if t.strip()]
            result.tables_markdown = [t for t in raw_tables if not is_likely_fake_table(t)]
        except Exception as e:
            result.warnings.append(f"Échec extraction tableaux: {e}")
    
    # 4) Extraction des images
    try:
        result.images_extracted = extract_images(
            doc, page, output_dir, doc_name, use_vision_llm
        )
    except Exception as e:
        result.warnings.append(f"Échec extraction images: {e}")
    
    return result


def extract_images(doc: fitz.Document, page: fitz.Page, output_dir: str, 
                   doc_name: str, use_vision_llm: bool) -> list:
    extracted = []
    image_list = page.get_images(full=True)
    
    for idx, img in enumerate(image_list):
        xref = img[0]
        try:
            base_image = doc.extract_image(xref)
        except Exception:
            continue
        
        width, height = base_image.get("width", 0), base_image.get("height", 0)
        if width < MIN_IMAGE_SIZE_PX or height < MIN_IMAGE_SIZE_PX:
            continue
        
        ext = base_image["ext"]
        img_filename = f"{doc_name}_p{page.number + 1}_img{idx + 1}.{ext}"
        img_path = os.path.join(output_dir or "/tmp", "images", img_filename)
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        
        with open(img_path, "wb") as f:
            f.write(base_image["image"])
        
        description = describe_image_with_vision_llm(img_path, use_vision_llm)
        extracted.append({"path": img_path, "description": description})
    
    return extracted