# ocr-research
research project about OCR

# instructions
1. Run `python Main.py`.
1. Select PDF files to scan. Multiple are acceptable.
1. Select a Format or create a new one.
	- Format creation (will rebound back to selection after)
		1. Type a name for the Format.
		1. Click on the PDF to make bounding boxes, where the program will later OCR the text.
			- Due to limited editing functions, you will have to restart the process if you mess up.
		1. Click next. The Format selection box will open again.
1. The output file can be found in the output folder of the directory.

# terminology
- Format - a configuration that determines the areas to scan in each file, meaning that each file scanned needs to be in the same "format".

# dependencies
\(You can just install using [requirements.txt](/requirements.txt)\)
- [tesseract](https://github.com/tesseract-ocr/tesseract)
- PyMuPDF
- Pillow
- pytesseract

**Note**: Make sure that the directory `C:/Program Files/Tesseract-OCR/tessdata` exists \(and that `tesseract` is registered as a CMD command?\).
