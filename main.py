import os, sys, time
import csv # data output
import pickle # format saving/loading
import configparser # config file
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames
import fitz
from PIL import Image, ImageTk
from FormatTools import *
import pytesseract as pytess

# script's directory
DIR = os.path.abspath(os.path.dirname(__file__))

# import configuration
configpath = os.path.join(DIR, 'config.ini')
config = configparser.ConfigParser()
config.read(configpath)
PRELOAD = config.getboolean('CONSTANT', 'preload_pdf')
OUTPUT_DIR = os.path.join(DIR, config.get('CONSTANT', 'output'))

# variable for caching assets
ASSETCACHE = []

# language to scan for [TEMPORARY]
lang = "eng"

if sys.platform == 'win32':
	# Adjust window resolution
	from ctypes import windll
	windll.shcore.SetProcessDpiAwareness(1)

# Top level window
root = tk.Tk()
root.title("OCR PDF")
root.withdraw()


## FILE SELECTION
FILES = askopenfilenames(filetypes=[('PDF Files','*.pdf')],initialfile=config['file']['lastopened'])
if len(FILES) == 0:
	print("No file selected, exiting.")
	sys.exit()
# save last opened file
config['file']['lastopened'] = str(FILES)[1:-1].replace(',','').replace("'",'"')
with open(configpath, 'w') as cf: config.write(cf)
print(f"\nReading from {[os.path.basename(x) for x in FILES]}\n")
cur_doc = 0
doc: fitz.Document = fitz.open(FILES[cur_doc])
PAGES: int = doc.page_count # might be variable?

# Load new file onto 'doc' variable
def load_doc(n: int):
	global doc, cur_doc
	doc.close()
	doc = fitz.open(FILES[n])
	cur_doc = n

# TODO: Format selection menu


# Create a Format to specify where to scan for each page.
def create_format():
	new_format = Format()

	# configure row 1 (w/canvas) to stretch vertical
	root.rowconfigure(1, weight=1)
	# row 2 (bottom bar) to stretch horizontal
	#root.rowconfigure(2,)

	# instructions
	instr = ttk.Label(root, text="Click to make bounding boxes that will be scanned.")
	instr.grid(row=0, columnspan=2)

	# Convert page to image
	def page_to_img(page_id) -> Image:
		pix = doc[page_id].get_pixmap()
		# set the mode depending on alpha
		mode = "RGBA" if pix.alpha else "RGB"
		return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

	# pdf display
	imgframe = ttk.LabelFrame(root, padding=5, labelanchor='n', text='%i/%i'%(1,PAGES))
	imgframe.grid(row=1, column=1, sticky=tk.N+tk.S)

	# load first page onto canvas
	pg: int = 0 # track page to display
	tkimg = ImageTk.PhotoImage(page_to_img(pg))
	# use canvas to allow overlaying rectangles
	canvas = tk.Canvas(master=imgframe, width=tkimg.width(), height=tkimg.height())
	canvas.grid()
	imgid = canvas.create_image(0, 0, anchor=tk.NW, image=tkimg)

	# handler for canvas events
	clicked: bool = False
	p1: tuple = (0,0)
	def canvas_click(e):
		nonlocal clicked, p1

		if clicked:
			canvas.create_rectangle(p1[0],p1[1],e.x,e.y)
			rect = fitz.Rect(p1, (e.x, e.y))
			sa = ScanArea(pg, rect)
			print(sa.__dict__)
			new_format.append(sa)
			
		else: p1 = (e.x, e.y)

		print("%i, %i" % (e.x, e.y))
		print(doc[pg].get_pixmap().pixel(e.x,e.y))

		clicked = not clicked

	canvas.bind('<Button-1>', canvas_click)


	# Arrow page navigation
	# have to load these outsize func else garbage collector will yeet them
	arrowL = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowL.png')).resize((32,64)))
	arrowR = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowR.png')).resize((32,64)))
	ASSETCACHE.extend([arrowL, arrowR])
	def arrow_nav_init():
		arrowLLabel = tk.Label(root, image=arrowL)
		arrowRLabel = tk.Label(root, image=arrowR)
		arrowLLabel.grid(row=1, column=0, sticky=tk.E)
		arrowRLabel.grid(row=1, column=2, sticky=tk.W)
		def next_page(e): turn_page(1)
		def prev_page(e): turn_page(-1)
		arrowLLabel.bind('<Button-1>', prev_page)
		arrowRLabel.bind('<Button-1>', next_page)

	# Change page displayed
	def turn_page(n: int):
		nonlocal pg, tkimg
		
		pg = (pg + n) % PAGES
		imgframe.config(text='%i/%i'%(pg+1,PAGES)) # update page label

		tkimg = ImageTk.PhotoImage(page_to_img(pg))
		canvas.itemconfig(imgid, image=tkimg)
		return

	arrow_nav_init()

	# separate grid for bottom bar
	bottom_bar = ttk.Frame(root, borderwidth=1)
	bottom_bar.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E)
	bottom_bar.columnconfigure(3, weight=1)
	# Document navigation
	def docs_nav_init():
		docL = tk.Label(bottom_bar, text=" ← ", relief=tk.GROOVE)
		docR = tk.Label(bottom_bar, text=" → ", relief=tk.GROOVE)
		docL.grid(row=0, column=0, sticky=tk.W)
		docR.grid(row=0, column=1, sticky=tk.W)
		def next_doc(e): turn_doc(1)
		def prev_doc(e): turn_doc(-1)
		docL.bind('<Button-1>', prev_doc)
		docR.bind('<Button-1>', next_doc)
	
	# Change document displayed
	def turn_doc(n: int):
		nonlocal doc_info
		load_doc((cur_doc+n)%len(FILES))
		doc_info.config(text="Doc #%i: %s"%(cur_doc+1, os.path.basename(FILES[cur_doc])))
		turn_page(0)

	docs_nav_init()
	doc_info = ttk.Label(bottom_bar, text="Doc #%i: %s"%(cur_doc+1, os.path.basename(FILES[cur_doc])))
	doc_info.grid(row=0, column=2, sticky=tk.W)

	# 'Next' button
	def next(): # TODO: handle when no areas have been selected
		# TODO: continue to language selection
		root.withdraw()
		root.quit()
		scan_docs(new_format)
	btn_next = ttk.Button(bottom_bar, text="Next", command=next)
	btn_next.grid(row=0, column=3, sticky=tk.E)


# Scan docs using selected format
def scan_docs(format: Format):
	ts = time.strftime('%b-%d-%Y_%H%M%S', time.localtime())
	#doc[pg].get_pixmap(dpi=300, clip=rect).save()
	with open(os.path.join(OUTPUT_DIR,ts+'.csv'), 'w', newline='') as f:
		out = csv.writer(f)
		
		for n, fn in enumerate(FILES): # per file
			load_doc(n)
			rowdata = []
			for area in format: # per ScanArea
				pix = doc[area.page].get_pixmap(dpi=300, clip=area.rect)
				img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples_mv)
				rowdata.append(pytess.image_to_string(img, lang))
			out.writerow(rowdata)

create_format()

root.deiconify()
root.mainloop()
doc.close()