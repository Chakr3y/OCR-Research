import sys, csv, configparser
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from ctypes import windll
import fitz
from PIL import Image, ImageTk
import pytesseract as pytess

# import config.ini
configpath = 'config.ini'
config = configparser.ConfigParser()
config.read(configpath)
PRELOAD = config.get('CONSTANT', 'preload_pdf')

# language to scan for [TEMPORARY]
lang = "eng+tha"

# Adjust window resolution
windll.shcore.SetProcessDpiAwareness(1)

# Top level window
root = tk.Tk()
root.title("OCR PDF")
root.withdraw()

	# TODO: handling multiple files
## FILE SELECTION
FILE = askopenfilename(filetypes=[('PDF Files','*.pdf')],initialfile=config['file']['last opened'])
if FILE == '':
	print("No file selected, exiting.")
	sys.exit()
# save last opened file
config['file']['last opened'] = FILE
with open(configpath, 'w') as cf:
	config.write(cf)
print("\nReading from " + FILE + "\n")
doc = fitz.open(FILE)
PAGES = doc.page_count

# previews pdf with format
def create_format():
	global PAGES, doc

	# convert page to image
	def page_to_img(page_id):
		pix = doc[page_id].get_pixmap()
		# set the mode depending on alpha
		mode = "RGBA" if pix.alpha else "RGB"
		return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

	# pdf display
	imgframe = ttk.LabelFrame(root, padding=5, labelanchor='n', text='%i/%i'%(1,PAGES))
	imgframe.grid(row=0, column=1)

	# load first page
	pg = 0 # track page to display
	tkimg = ImageTk.PhotoImage(page_to_img(pg))
	image = tk.Label(imgframe, image=tkimg)
	image.grid()

	# arrow page navigation
	# have to load these outsize func else garbage collector will yeet them
	arrowL = ImageTk.PhotoImage(Image.open('assets/arrowL.png').resize((32,64)))
	arrowR = ImageTk.PhotoImage(Image.open('assets/arrowR.png').resize((32,64)))
	def arrow_nav_init():
		global root
		arrowLLabel = tk.Label(root, image=arrowL)
		arrowRLabel = tk.Label(root, image=arrowR)
		arrowLLabel.grid(row=0, column=0)
		arrowRLabel.grid(row=0, column=2)
		def next_page(e): turn_page(e, 1)
		def prev_page(e): turn_page(e, -1)
		arrowLLabel.bind('<Button-1>', prev_page)
		arrowRLabel.bind('<Button-1>', next_page)
	arrow_nav_init()

	# change page displayed
	def turn_page(e, n:int):
		nonlocal pg, imgframe, tkimg, image
		
		pg = (pg + n) % PAGES
		#print(pg)

		imgframe.config(text='%i/%i'%(pg+1,PAGES)) # update page label

		tkimg = ImageTk.PhotoImage(page_to_img(pg))
		image.config(image=tkimg)

		#print(pytess.image_to_string(doc[pg].pix_map()))
		return


	root.deiconify()
	root.mainloop()
create_format()

doc.close()