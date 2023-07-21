import os, sys, time
import csv # data output
import pickle # format saving/loading
import configparser # config file
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames
from tkinter.simpledialog import askstring
from tkinter.messagebox import showerror
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


## FILE SELECTION
FILES = askopenfilenames(filetypes=[('PDF Files','*.pdf')],initialfile=config['file']['lastopened'])
if len(FILES) == 0:
	print("No file selected, exiting.")
	sys.exit()
# save paths for last opened files
config['file']['lastopened'] = str(FILES)[1:-1].replace(',','').replace("'",'"')
with open(configpath, 'w') as cf: config.write(cf)
print(f"\nReading from {[os.path.basename(x) for x in FILES]}\n")

cur_doc = 0
doc: fitz.Document = None
pages: int = None

# Load new file onto 'doc' variable
def load_doc(n: int):
	global doc, cur_doc, pages
	if doc is not None: doc.close()
	doc = fitz.open(FILES[n])
	cur_doc = n
	pages = doc.page_count
load_doc(cur_doc)

# Top level window
root = tk.Tk()
root.title("OCR PDF")
root.withdraw()

# TODO: Format selection menu
format_list: list[str] = None
def format_select():
	global format_list
	# update list
	format_list = [os.path.splitext(os.path.basename(x))[0] for x in os.listdir(os.path.join(DIR, "formats"))]

	str_create = "Create a new Format..."
	format_list.append(str_create)
	
	root.deiconify()
	# frame container for widgets
	frame = ttk.Frame(root, borderwidth=25)
	frame.pack()

	desc = ttk.Label(frame, text="Select a Format.")
	desc.grid(row=0, column=0, sticky=tk.W)
	# dropdown selection
	select = ttk.Combobox(frame, exportselection=0, values=format_list)
	select.grid(row=1, column=0, sticky=tk.W+tk.E)
	# TODO: grey out button when none selected?
	# buttons
	def proceed():
		selection = select.get()
		if selection == "":
			pass
		elif selection == str_create:
			root.withdraw()
			frame.destroy()
			create_format()
			return
		elif selection in format_list:
			# TODO: implement previewing?
			with open(os.path.join(DIR, "formats", selection+".pkl"), 'rb') as f:
				format = pickle.load(f)
				scan_docs(format)
		else: pass
		return		

	btn_next = ttk.Button(frame, text="Next", command=proceed)
	btn_next.grid(row=2, column=0, sticky=tk.E, pady=(20, 0))


# Create a Format to specify where to scan for each page.
def create_format():
	f_name = askstring("OCR PDF", "Enter a name for the new Format.")
	if f_name == "": # rebound back to format selection
		format_select()
		return
	
	while f_name in format_list: # duplicate name
		showerror("Error", "This name has already been used by a Format.")
		f_name = askstring("OCR PDF", "Enter a name for the new Format.", initialvalue=f_name)

	root.deiconify()
	format = Format(f_name)

	# frame container for widgets
	frame = ttk.Frame(root)
	frame.pack(expand=1)

	# configure row 1 (w/canvas) to stretch vertical
	frame.rowconfigure(1, weight=1)

	# instructions
	instr = ttk.Label(frame, text="Click to make bounding boxes that will be scanned.")
	instr.grid(row=0, columnspan=2)

	# Convert page to image
	def page_to_img(page_id) -> Image:
		pix = doc[page_id].get_pixmap()
		# set the mode depending on alpha
		mode = "RGBA" if pix.alpha else "RGB"
		return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

	# pdf display
	imgframe = ttk.LabelFrame(frame, padding=5, labelanchor='n', text='%i/%i'%(1,pages))
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
			format.append(sa)
			update_areanum()
		else: p1 = (e.x, e.y)

		print("{e.x}, {e.y}")
		#print(doc[pg].get_pixmap().pixel(e.x,e.y))
		clicked = not clicked

	canvas.bind('<Button-1>', canvas_click)

	# Arrow page navigation
	# have to load these outsize func else garbage collector will yeet them
	arrowL = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowL.png')).resize((32,64)))
	arrowR = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowR.png')).resize((32,64)))
	ASSETCACHE.extend([arrowL, arrowR])
	def arrow_nav_init():
		arrowLLabel = tk.Label(frame, image=arrowL)
		arrowRLabel = tk.Label(frame, image=arrowR)
		arrowLLabel.grid(row=1, column=0, sticky=tk.E)
		arrowRLabel.grid(row=1, column=2, sticky=tk.W)
		def next_page(e): turn_page(1)
		def prev_page(e): turn_page(-1)
		arrowLLabel.bind('<Button-1>', prev_page)
		arrowRLabel.bind('<Button-1>', next_page)

	# Change page displayed
	def turn_page(n: int):
		nonlocal pg, tkimg
		
		pg = (pg + n) % pages
		imgframe.config(text='%i/%i'%(pg+1,pages)) # update page label

		tkimg = ImageTk.PhotoImage(page_to_img(pg))
		canvas.itemconfig(imgid, image=tkimg)
		return

	arrow_nav_init()

	# separate grid for bottom bar
	b_line = ttk.Separator(frame)
	b_line.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E)
	bottom_bar = ttk.Frame(frame, borderwidth=1)
	bottom_bar.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E)
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
	# label for current document
	doc_info = ttk.Label(bottom_bar, text="Doc #%i: %s"%(cur_doc+1, os.path.basename(FILES[cur_doc])))
	doc_info.grid(row=0, column=2, sticky=tk.W)
	
	# display number of boxes made
	area_num = ttk.Label(bottom_bar, text="Areas: 0")
	area_num.grid(row=0, column=3)
	def update_areanum():
		area_num.config(text="Areas: %i"%len(format))

	# 'Next' button
	def proceed(): # TODO: handle when no areas have been selected
		# TODO: continue to language selection
		
		# save format as a file
		with open(os.path.join(DIR, "formats", format.name + ".pkl"), 'xb') as f:
			pickle.dump(format, f)
		root.withdraw()
		frame.destroy()
		format_select()
	btn_next = ttk.Button(bottom_bar, text="Next", command=proceed)
	btn_next.grid(row=0, column=4, sticky=tk.E)


# Scan docs using selected format
def scan_docs(format: Format):
	root.quit()
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

format_select()

root.mainloop()
doc.close()