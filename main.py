import tkinter
from tkinter.filedialog import askopenfilename
import fitz

# Tesseract data on computer
TESSDATA = "C:/Program Files/Tesseract-OCR/tessdata"

# language to OCR
lang = "tha+eng"

if __name__ == '__main__':
	# prompt user to select a PDF to scan
	tkinter.Tk().withdraw()
	FILE = askopenfilename()
	#FILE = "C:/Users/Chakrey/Documents/2023-06-23_185013.pdf"


	print("\nReading from " + FILE + "\n")
	doc = fitz.open(FILE)
	p = doc.load_page(0)
	tp = p.get_textpage_ocr(full=False, language=lang, tessdata=TESSDATA, flags=8)

	print(tp.extractText())

	doc.close()
	