import fitz

# Tesseract data on computer
TESSDATA = "C:/Program Files/Tesseract-OCR/tessdata"

# PDF document to scan
file = "./Stellar_Engines.pdf"

doc = fitz.open(file)
p = doc.load_page(0)

print(p.get_textpage_ocr(tessdata=TESSDATA).extractText())

doc.close()