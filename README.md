# ocr-research
Experimental project about using OCR to compile text on PDFs into CSVs.
The user specifies static bounding boxes to feed into OCR. This means that text between different documents need to be in the same exact location, as the program will not detect text shifting slightly.

# output format
Each file scanned will have the text extracted into the same row, per file.

# instructions
1. Run `python main.py`.
1. Select PDF files to scan. Multiple are acceptable.
1. Select a Format or create a new one.
	- Format creation (will return back to Format selection afterward)
		1. Type a name for the Format.
		1. Click on the PDF to make bounding boxes, where the program will later OCR the text.
			- Undo button to be implemented
		1. Select language to scan for.
			- The program will automatically detect installed language packs for tesseract.
1. Select Scan or Preview
	- Preview displays the selected PDFs with bounding boxes overlaid where the file will be scanned for text. Scan will immediately skip this step.
1. The output file can be found in the [`output`](/output) folder of the directory.

- For the time being, Formats can be deleted by deleting the file with the corresponding name in the [`formats`](/formats) folder.

If the output is inaccurate, try expanding the scanning area.

# terminology
- Format - a scanning configuration that groups areas to scan in a batch of files \(each file scanned needs to have text at the same locations\)

# dependencies
- [tesseract](https://github.com/tesseract-ocr/tesseract)

Python dependencies \(install using [requirements.txt](/requirements.txt)\)
- PyMuPDF
- Pillow
- pytesseract

**Note**: Make sure that the directory `C:/Program Files/Tesseract-OCR/tessdata` exists \(and that `tesseract` is registered as a CMD command?\).

# todo
- Refactor for readability
- Finish Format creator UI
	- [ ] Undo button
	- [ ] Add naming/numbering scan areas
- Improve OCR
