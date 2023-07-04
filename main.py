import sys, csv
import tkinter
from tkinter.filedialog import askopenfilename
import ocrmypdf

# Tesseract data on computer
TESSDATA = "C:/Program Files/Tesseract-OCR/tessdata"

# language to OCR
lang = "tha+eng"

if __name__ == '__main__':
	# prompt user to select a PDF to scan
	"""tkinter.Tk().withdraw()
	FILE = askopenfilename()"""
	FILE = "C:/Users/Chakrey/Documents/2023-06-23_185013.pdf"

	print("\nReading from " + FILE + "\n")

	ocrmypdf.ocr(FILE, "output.pdf", language=lang)
	