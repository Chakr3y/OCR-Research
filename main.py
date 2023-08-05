import os, sys, time
import csv # data output
import pickle # format saving/loading
import configparser # config file
from FormatTools import *

import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames
from tkinter.simpledialog import askstring, Dialog
from tkinter.messagebox import showerror

import fitz
from PIL import Image, ImageTk
import pytesseract as pytess

# script's directory
DIR = os.path.abspath(os.path.dirname(__file__))

# import configuration
CONFIG_PATH = os.path.join(DIR, 'config.ini')
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

DO_PRELOAD = config.getboolean('CONSTANT', 'preload_pdf')
OUTPUT_DIR = os.path.join(DIR, config.get('CONSTANT', 'output'))

# variable for caching assets
ASSET_CACHE = []

# available language packs installed for tesseract
LANGS = pytess.get_languages()
if "osd" in LANGS: LANGS.remove("osd")


if sys.platform == 'win32': # Adjust window resolution
	from ctypes import windll
	windll.shcore.SetProcessDpiAwareness(1)


## FILE SELECTION
FILES = askopenfilenames(filetypes=[('PDF Files','*.pdf')],initialfile=config['file']['lastopened'])
if len(FILES) == 0:
	print("No file selected, exiting.")
	sys.exit()

# save paths for last opened files
config['file']['lastopened'] = str(FILES)[1:-1].replace(',','').replace("'",'"')
with open(CONFIG_PATH, 'w') as cf: config.write(cf)

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
	return
load_doc(cur_doc)


# Top level window
root = tk.Tk()
root.title("OCR PDF")
root.withdraw() # start hidden


# Format selection menu
format_list: list[str] = None
def format_from_name(name: str) -> Format:
	with open(os.path.join(DIR, "formats", name+".pkl"), 'rb') as f:
		return pickle.load(f)

def format_select():
	global format_list

	# update list of saved formats
	format_list = [os.path.splitext(os.path.basename(x)) for x in os.listdir(os.path.join(DIR, "formats"))]
	format_list = filter(lambda x: x[1] == ".pkl", format_list)
	format_list = [x[0] for x in format_list]

	str_create = "Create a new Format..."
	format_list.append(str_create)
	
	root.deiconify()

	
	# frame container for widgets
	frame = ttk.Frame(root, borderwidth=25)
	frame.pack()

	desc = ttk.Label(frame, text="Select a Format.")
	desc.grid(row=0, column=0, sticky=tk.W)
	
	# dropdown selection
	def verify(): # dynamically react to selection
		selection = select.get()
		
		if selection in format_list:
			btn_next.state(["!disabled"])
			btn_preview.state([("" if selection == str_create else "!")+"disabled"])

			return True
		
		btn_next.state(["disabled"])
		btn_preview.state(["disabled"])
		return False
	v = frame.register(verify)
	select = ttk.Combobox(frame, exportselection=0, values=format_list, validate='all', validatecommand=v)
	select.grid(row=1, column=0, sticky=tk.W+tk.E)
	

	# TODO: grey out button when none selected?
	def proceed(e = None):
		selection = select.get()

		if selection == str_create:
			root.withdraw()
			frame.destroy()
			display_pdf()
		elif selection in format_list:
			scan_docs(format_from_name(selection))
		else: pass

	# pressing enter = click next
	select.bind("<Return>", proceed)

	# preview overlaying the Format over pdf
	def preview(e = None):
		selection = select.get()
		if selection in format_list:
			root.withdraw()
			frame.destroy()
			display_pdf(format_from_name(selection))


	# buttons
	# stolen code from Dialog class
	btn_box = tk.Frame(frame)

	btn_next = ttk.Button(btn_box, text="Next", width=10, command=proceed, default=tk.ACTIVE)
	btn_next.pack(side=tk.RIGHT, padx=5, pady=5)
	btn_next.state(["disabled"])
	btn_preview = ttk.Button(btn_box, text="Preview", width=10, command=preview)
	btn_preview.pack(side=tk.RIGHT, padx=5, pady=5)
	btn_preview.state(["disabled"])

	btn_box.grid()
	return


def page_to_img(page_id) -> Image: # Convert page to image
	pix = doc[page_id].get_pixmap()
	# set the mode depending on alpha
	mode = "RGBA" if pix.alpha else "RGB"
	return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

# Display a preview or create a Format
def display_pdf(format: Format = None):
	# specify parameter to view pdf, otherwise create a new Format
	PREVIEW = bool(format)

	if not PREVIEW: # Format naming
		f_name = askstring("OCR PDF", "Enter a name for the new Format.")
		if f_name == "": # rebound back to format selection
			format_select()
			return
		
		while f_name in format_list: # name already in use
			showerror("Error", "This name has already been used by a Format.")
			f_name = askstring("OCR PDF", "Enter a name for the new Format.", initialvalue=f_name)
		
		format = Format(f_name)

	root.deiconify()

	# frame container for widgets
	frame = ttk.Frame(root)
	frame.pack(expand=1)
	frame.rowconfigure(1, weight=1) # stretch vertically

	# text instructions
	str_instr = "Previewing Format." if PREVIEW\
		else "Click to make bounding boxes that will be scanned."
	instr = ttk.Label(frame, text=str_instr)
	instr.grid(row=0, columnspan=2)


	# frame for canvas displaying PDF, label shows page number
	imgframe = ttk.LabelFrame(frame, padding=5, labelanchor='n', text='%i/%i'%(1,pages))
	imgframe.grid(row=1, column=1, sticky=tk.N+tk.S)

	# load first page onto canvas
	pg: int = 0 # track page number
	tkimg = ImageTk.PhotoImage(page_to_img(pg))
	canvas = tk.Canvas(master=imgframe, width=tkimg.width(), height=tkimg.height())
	canvas.grid()

	img_id = canvas.create_image(0, 0, anchor=tk.NW, image=tkimg)
	get_pg_rects = lambda pg: "p"+str(pg)

	def create_rect(x1, y1, x2, y2, pg=pg, n=len(format)):
		canvas.create_rectangle(x1, y1, x2, y2, outline="red", tags=("rect", get_pg_rects(pg), str(n)))


	# Arrow page navigation
	# have to load these outside func else garbage collector will yeet them
	arrowL = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowL.png')).resize((32,64)))
	arrowR = ImageTk.PhotoImage(Image.open(os.path.join(DIR,'assets/arrowR.png')).resize((32,64)))
	ASSET_CACHE.extend([arrowL, arrowR])
	def arrow_nav_init(): # navigation through pages
		arrowLLabel = tk.Label(frame, image=arrowL)
		arrowRLabel = tk.Label(frame, image=arrowR)
		# render next to canvas
		arrowLLabel.grid(row=1, column=0, sticky=tk.E)
		arrowRLabel.grid(row=1, column=2, sticky=tk.W)
		def next_page(e): turn_page(1)
		def prev_page(e): turn_page(-1)
		arrowLLabel.bind('<Button-1>', prev_page)
		arrowRLabel.bind('<Button-1>', next_page)

	# Change page displayed
	def turn_page(direction: int):
		nonlocal pg, tkimg
		
		pg = (pg + direction) % pages
		imgframe.config(text='%i/%i'%(pg+1,pages)) # update page label

		# change image data
		tkimg = ImageTk.PhotoImage(page_to_img(pg))
		canvas.itemconfig(img_id, image=tkimg)

		# display corresponding rects
		print(get_pg_rects(pg))
		canvas.tag_lower("rect", img_id)
		canvas.tag_raise(get_pg_rects(pg), img_id)

	arrow_nav_init()


	if PREVIEW: # load in rects
		print(format.__dict__)
		for n, sa in enumerate(format):
			create_rect(sa.p1[0], sa.p1[1], sa.p2[0], sa.p2[1], sa.page, n)
		turn_page(0)
		
	else: # handler for canvas events

		clicked: bool = False # remember alternate clicks
		p1: tuple = (0,0) # previous click location
		def canvas_click(e):
			nonlocal clicked, p1

			if clicked:
				# create a red bounding box surrounding the scan area, tag with pg and number
				create_rect(p1[0], p1[1], e.x, e.y)
				rect = fitz.Rect(p1, (e.x, e.y))
				sa = ScanArea(pg, rect)
				#print(sa.__dict__)
				format.append(sa)

				update_areanum()
			else: p1 = (e.x, e.y)

			print("{e.x}, {e.y}")
			#print(doc[pg].get_pixmap().pixel(e.x,e.y))
			clicked = not clicked
		
		canvas.bind('<Button-1>', canvas_click)


	# Bottom portion of the GUI
	separator = ttk.Separator(frame)
	separator.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E)
	# separate frame for bottom elements
	bottom_bar = ttk.Frame(frame, borderwidth=1)
	bottom_bar.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E)
	bottom_bar.columnconfigure(3, weight=1)

	# Document navigation at bottom left
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
		nonlocal doc_label

		load_doc((cur_doc+n)%len(FILES))
		# change label
		doc_label.config(text="Doc #%i: %s"%(cur_doc+1, os.path.basename(FILES[cur_doc])))
		turn_page(0)

	docs_nav_init()

	# label current document num and file name
	# TODO: shorten file name if too long or restrict size
	doc_label = ttk.Label(bottom_bar, text="Doc #%i: %s"%(cur_doc+1, os.path.basename(FILES[cur_doc])))
	doc_label.grid(row=0, column=2, sticky=tk.W)
	
	# display number of boxes made
	area_num = ttk.Label(bottom_bar, text="Areas: 0")
	area_num.grid(row=0, column=3)
	def update_areanum():
		area_num.config(text="Areas: %i"%len(format))

	if PREVIEW: update_areanum()

	# After areas have been selected
	def proceed(): # TODO: handle when no areas have been selected

		class LangSelDialog(Dialog): # lanugage selection
			def body(self, root = None):
				# Create a list of options
				self._options = LANGS

				# for scrolling vertically
				yscrollbar = tk.Scrollbar(root)
				yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

				label = tk.Label(root,
					text = "Select languages to scan for",
					padx = 10, pady = 10)
				label.pack()
				self.lb = tk.Listbox(root, selectmode = "multiple", 
					yscrollcommand = yscrollbar.set)

				# Widget expands horizontally and vertically by assigning both to fill option
				self.lb.pack(padx = 10, pady = 10,
					expand = tk.YES, fill = "both")

				# Add options to the Listbox
				for option in self._options:
					self.lb.insert(tk.END, option)

				return root

			# call to determine if selection is appropriate to continue
			def validate(self):
				return len(self.lb.curselection()) > 0
			
			# called after 'OK' and valid
			def apply(self):
				sel = [self.lb.get(i) for i in self.lb.curselection()]
				#print(sel)

				# set language option for format
				format.lang = "+".join(x for x in sel)
				print(format.lang)

				# save format as a file
				with open(os.path.join(DIR, "formats", format.name + ".pkl"), 'xb') as f:
					pickle.dump(format, f)
				
				# clear the window and go back to format selection
				root.withdraw()
				frame.destroy()
				format_select()

		if PREVIEW:
			scan_docs(format)
		else:
			ls = LangSelDialog(None)
	
	str_next = "Scan" if PREVIEW else "Next"
	btn_next = ttk.Button(bottom_bar, text=str_next, command=proceed)
	btn_next.grid(row=0, column=4, sticky=tk.E)
	
	return


# Scan docs using selected format
def scan_docs(format: Format):
	root.quit()
	# put a timestamp in the file name
	ts = time.strftime('%b-%d-%Y_%H%M%S', time.localtime())
	#doc[pg].get_pixmap(dpi=300, clip=rect).save()

	output_path = os.path.join(OUTPUT_DIR, f'{format.name}-{ts}.csv')
	with open(output_path, 'w', newline='') as f:
		out = csv.writer(f)
		
		for n, fn in enumerate(FILES): # per file
			load_doc(n)
			
			rowdata = []
			for area in format: # per ScanArea
				pix = doc[area.page].get_pixmap(dpi=300, clip=area.rect)
				img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples_mv)
				rowdata.append(pytess.image_to_string(img, format.lang))
			
			out.writerow(rowdata)
	return


format_select()
root.mainloop()

doc.close()