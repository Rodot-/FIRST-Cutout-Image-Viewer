#!/usr/bin/env python
'''
Tool for viewing image cutouts from the VLA FIRST survey.

Powered by Anaconda
More in depth
Description here
'''
import re, os, urllib2, urllib, socket, sys, itertools, shutil, time
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.backend_bases import key_press_handler
from matplotlib.pyplot import figure
import numpy as np
from astropy.coordinates import Angle
from astropy.io import fits
try:
	import eventlet
	from eventlet.green import urllib2, urllib, socket
	from eventlet import GreenPool
	GEVENT = True
except ImportError as e:
	print "ImportError:", e
	print "Using Standard Modules"
	print "  Downloading will be Painfully Slow"
	print "Please Install Eventlet by:"
	print "  --> pip install eventlet"
	GEVENT = False
if sys.version_info[0] < 3:
	import Tkinter as Tk
else:
	import tkinter as Tk

try:
	import tkFileDialog
	TKDIAG = True
except ImportError as e:
	print "ImportError:", e
	print "User will be restricted to "
	print "command line arguments for downloading"
	TKDIAG = False
#Setup
#Check if the cutoutfolder exists. If not: create it.
IMAGE_PATH = 'FIRST_Cutouts' #Path to image cutouts
if not os.path.exists(IMAGE_PATH):os.makedirs(IMAGE_PATH)

#CONSTANTS:
##Program Parameters
CMAP = 'jet' #Color map for the image plots
MEMMAP = True #Use memory mapping while opening fits files?
REMOVE_FAILED_LOADS = True #Should Incomplete FITS files be removed?
IMAGE_SIZE = 5.0 #Image size in arc-minutes
DISPLAY_SIZE = 15.0 #Display size in arc-minutes, not functional
IMAGE_TYPE = "FITS_File" #Type of image to return
GREEN_POOL_SIZE = 32 #Size of Greenpool: number of concurrent download threads
TARGET = "http://third.ucllnl.org/cgi-bin/firstcutout" 
'''string: Website we target to extract the image cutouts.'''
##Regular Expressions
COORD_REGEX = "(?P<ms>([+\-]?\d{1,2})(?:(?P<s>[: ])|(?P<f>(?:h|d)))(\d{1,2})(?(f)m|(?P=s))([\d.]+)(?(f)s|\d$))|(?P<deg>^([+\-]?(?=[\d.]).)*$)"
'''string: Regular expression for determining the format of input coordinates.

Used for discovering the format of an input coordinate
	so that it may be changed to a desired format.

Groups:
	ms: matching string is formatted in hms/dms
	s: separator if string is formatted in hms/dms (colon or white space)
	f: the characters hms or dms are used as the separators 
	deg: matching string is formatted in decimal degrees
'''
NAME_REGEX = r"(\d{2} \d{2} \d{2}\.\d{2})\d* ([+\-]\d{2} \d{2} \d{2}\.\d)"
'''string: Regular expression for generating the object name'''
#Compile the regex functions
coord_com = re.compile(COORD_REGEX)
name_com = re.compile(NAME_REGEX)
##Other
current_files = os.listdir(IMAGE_PATH)
'''The list of files already downloaded.

Used to make sure we don't download duplicates.
'''
#Mutable global variable
fields = {'RA':"","ImageType":IMAGE_TYPE,"ImageSize":IMAGE_SIZE}
'''Dictionary of URL parameters to be encoded.

Will be updated for each object.

Keys:
	RA (string): full coordinate formed by 
		angle of right ascension in sexagesimal
		coordinates separated by single spaces
		joined by a single space with
		declination in sexagesimal coodinates
		separated by single spaces
	ImageType (string): image format requested
	ImageSize (int): size of image in arc-minutes
'''
#Special Characters
RIGHT_ARROW = u'\u25B6'
LEFT_ARROW = u'\u25C0'
DOWN_ARROW = u'\u25BC'
DOWN_ARROW = u'\u2193'
SIGMA = u'\u03A3'
###

def reformat(coord, unit): 
	'''Reformats a coordinate based on the unit.

	Args:
		coord (string): angle of right ascention or declination
		unit (string): the output format (h for hms, deg for dms)

	Returns:
		coord (string): formatted coordinate

	Raises:
		SyntaxError: If 'coord' is not in a valid format
	'''
	result = coord_com.search(coord) #Check if the coordinate is valid
	if result is None: raise SyntaxError("Error: Incorrect Format", coord)
	if result.group('deg') is not None: #Coordinate is in degree format
		coord = Angle(result.group('deg') + 'd').to_string(unit, sep = ' ', alwayssign = True, pad = True, precision = 8)
	else: #Coordinate is in sexagesimal format
		if result.group('s') is not None: #Separated by colon or space
			if result.group('s') == ':':
				coord = ' '.join(result.group('ms').split(':'))
			else:
				coord = result.group('ms')
		else: #separated by hms/dms
			coord = Angle(result.group('ms')).to_string(unit, sep = ' ', alwayssign = True, pad = True, precision = 8)
	return coord	

def getData(RA,DEC): 
	'''Encodes the url data of the RA and DEC for use by getCutout.

	Args:
		RA (string): angle of right ascension
		DEC (string): declination
	
	Returns:
		None: if the cutout is already downloaded

		data (string): url encoded data to be sent to the target
		name (string): a filename to download the object to
	'''
	coord = " ".join((reformat(RA, 'h'), reformat(DEC, 'deg')))
	name = "SDSS_J"+"".join("".join(name_com.search(coord).groups()).split())+".fits"
	fields['RA'] = coord #fields['RA'] is actually the entire coordinate
	if name not in current_files: #Check if the file is already downloaded
		data = urllib.urlencode(fields)
		return data, name 

def getCutout(data, name):
	'''Downloads the image cutout to a file.

	Args: 
		see 'Returns' of 'getData'

	Returns:
		status (int): 1 for sucessful download
			0 for unsucessful download
		name (string): name of the created file
	'''
	try:
		req = urllib2.Request(TARGET, data)
		resp = urllib2.urlopen(req, None, 10)
		with open('/'.join((IMAGE_PATH,name)),'wb') as f:
			f.write(resp.read())
		status = 1 #Success, 0 implies failure
	except urllib2.URLError, err:
		print "urllib2.URLError:",err.reason
		status = 0
	except socket.timeout, err: #Took too long to download
		print "socket.timeout:",err
		status = 0
	finally: #Try to clean up 
		try:
			resp.close()
		except NameError:
			pass
	return status, name

def genFromFile(file_name): 
	'''Generates RA,DEC pairs from a file for use in downloadCutouts.

	Args:
		file_name (string): input file name

	Returns:
		columns (list): Nx2 list where N is the number
		of objects; first column being RA, second column
		being DEC
	'''
	with open(file_name,'rb') as inFile:
		columns = [row.strip().split(',') for row in inFile]
	return columns

def downloadCutouts(coord_list): 
	'''Downloads cutouts from a list of RA, DEC pairs

	Args:
		coord_list (list): Nx2 list where N is the number
		of object; first column being RA, decond column
		being DEC
	'''
	print "Generating URLs"
	raw_params = (getData(RA, DEC) for RA, DEC in coord_list)
	params = (param for param in raw_params if param is not None)
	print "Downloading"

	if GEVENT: #Did we sucessfully import concurrent downloading library?
		P = GreenPool(GREEN_POOL_SIZE)
		for status, name in P.starmap(getCutout, params):
			print '{:<30}'.format(name), status
	else: #Use the slower default functions instead
		for status, name in itertools.starmap(getCutout, params):
			print '{:<30}'.format(name), status

	print "Done"	

class Stacker(Tk.Frame): #Custom Widget for Managing which Objects get Stacked
	'''
	Custom Widget for Managing Which Objects get Stacked.

	Provides a few convenience functions for interacting with 
	the main interface.
	Allows the user to move and manipulate items between two columns
	'''	

	#Regular Expression to extract the name of valid files.
	regex = r'J\d{6}\.\d{2}[+\-]\d{6}\.\d{1}'
	com = re.compile(regex)
	#TODO: It might be a good idea to abstract this
	# as a method to convert back and forth.
	# Also, could help manage files that do not follow
	# the naming convention

	def __init__(self, master):

		Tk.Frame.__init__(self, master)
		self.master = master
		self.createWidgets()
		self.initWidgets()
		self.packWidgets()
		self.bindWidgets()
	
	def createWidgets(self):
		'''
		Creates all widgets to be used by the class.

		Quick overview of a few frames:
		-listboxFrame: Holds Listboxes and Transfer Buttons
		-buttonFrame: Holds Buttons for general Manipulation
		-pushpullFrame: Holds Transfer Buttons
		'''

		push_text = ''.join(('Add ', RIGHT_ARROW))
		pull_text = ''.join((LEFT_ARROW, ' Remove'))

		description = '''Chose which objects you would like to stack.\nSelect an object to view it on the canvas.'''

		self.listboxFrame = Tk.LabelFrame(self, padx = 5, pady = 5)
		self.buttonFrame = Tk.Frame(self)
		self.pushpullFrame = Tk.Frame(self.listboxFrame, padx = 5)
		self.descriptionFrame = Tk.Frame(self)
		self.infoFrame = Tk.LabelFrame(self)
		self.unstackable_scroller = Tk.Scrollbar(self.listboxFrame, orient = Tk.VERTICAL)
		self.stackable_scroller = Tk.Scrollbar(self.listboxFrame, orient = Tk.VERTICAL)
		self.unstackable = Tk.Listbox(self.listboxFrame, selectmode = Tk.EXTENDED, yscrollcommand = self.unstackable_scroller.set)
		self.stackable = Tk.Listbox(self.listboxFrame, selectmode = Tk.EXTENDED, yscrollcommand = self.stackable_scroller.set)

		self.pusher = Tk.Button(self.pushpullFrame, text = push_text, command = self.push)
		self.puller = Tk.Button(self.pushpullFrame, text = pull_text, command = self.pull)


		self.description = Tk.Label(self.descriptionFrame, text = description, padx = 5, pady = 5)

	def update_listboxes(self, *file_names):
		'''More of an initialization.'''

		names = filter(None,map(self.com.search, file_names))
		for name in names:self.unstackable.insert(Tk.END,name.group())
		self.update()		

	def initWidgets(self):
		'''
		Initialize widgets that require extra configuration.

		In this case, we start by filling the
		list of objects that are not planned
		to be stacked with the names converted
		by our regex.  We then configure
		the scrollers to scroll their respective widgets
		'''

		names = filter(None,map(self.com.search, self.master.files))
		for name in names:self.unstackable.insert(Tk.END,name.group())
		self.unstackable_scroller.config(command = self.unstackable.yview)
		self.stackable_scroller.config(command = self.stackable.yview)
		 
	def packWidgets(self):

		self.descriptionFrame.pack(side = Tk.TOP, fill = Tk.X, expand = 0, anchor = Tk.N)
		self.description.pack(side = Tk.LEFT, fill = Tk.X, expand = 0, anchor = Tk.N)
		self.listboxFrame.pack(side = Tk.TOP, fill = Tk.BOTH, expand = 0)
		self.unstackable.pack(side = Tk.LEFT, fill = Tk.Y, expand = 1)
		self.unstackable_scroller.pack(side = Tk.LEFT, fill = Tk.Y, expand = 1)
		self.stackable_scroller.pack(side = Tk.RIGHT, fill = Tk.Y, expand = 1)
		self.stackable.pack(side = Tk.RIGHT, fill = Tk.Y, expand = 1)
		self.pushpullFrame.pack(expand = 1, fill = Tk.Y, anchor = Tk.CENTER)
		self.pusher.pack(side = Tk.TOP, fill = Tk.X, expand = 1, anchor = Tk.S)
		self.puller.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 1, anchor = Tk.N)

		self.infoFrame.pack(side = Tk.BOTTOM, fill = Tk.BOTH, expand = 1)

		self.buttonFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)


	def bindWidgets(self):
		'''Event Bindings for Various Widgets'''
		self.event_add('<<SingleSelect>>','<Button-1>','<Up>','<Down>')

		self.unstackable.bind('<Double-Button-1>', self.push)
		self.stackable.bind('<Double-Button-1>', self.pull)

		self.unstackable.bind('<Button-3>', self.on_right_click)
		self.stackable.bind('<Button-3>', self.on_right_click)

		self.unstackable.bind('<<SingleSelect>>', self.test_click_select)
		self.stackable.bind('<<SingleSelect>>', self.test_click_select)

	def file_sort(self, stack, parent_stack):
		'''Sort a list of object names based on the ordering
		in same master list of file names associated with the object'''

		mapping = dict([(f[5:-5],i) for i,f in enumerate(parent_stack)])
		def key(x):
			try: 
				return mapping[x]+1
			except KeyError as e:
				return None
		stack = filter(key, stack)
		return sorted(tuple(stack), key = lambda x: mapping[x])

	def push(self, event = None):
		'''Move and object from the left listbox to the right'''

		selection = self.unstackable.curselection()
		ustack = self.unstackable.get(0,Tk.END)
		stack = self.stackable.get(0,Tk.END)
		items = set([ustack[i] for i in selection])
		ustack = set(ustack) - items

		items = self.file_sort(stack+tuple(items), self.master.files)
		ustack = self.file_sort(ustack, self.master.files)

		self.unstackable.delete(0,Tk.END)
		self.stackable.delete(0,Tk.END)
		self.stackable.insert(Tk.END, *items)
		self.unstackable.insert(Tk.END, *ustack)

		self.see_item(self.master.files[self.master.pos])
		self.update()
		
	def pull(self, event = None):
		'''Move and object from the right listbox to the left'''		
		selection = self.stackable.curselection()
		stack = self.stackable.get(0,Tk.END)
		ustack = self.unstackable.get(0,Tk.END)
		items = set([stack[i] for i in selection])
		stack = set(stack) - items

		items = self.file_sort(tuple(items)+ustack, self.master.files)
		stack = self.file_sort(stack, self.master.files)

		self.stackable.delete(0,Tk.END)
		self.unstackable.delete(0,Tk.END)
		self.unstackable.insert(Tk.END, *items)
		self.stackable.insert(Tk.END, *stack)

		self.see_item(self.master.files[self.master.pos])
		self.update()

	def get_stackable(self):
		'''Returns a list of file names from the right listbox'''

		return [s.join(('SDSS_','.fits')) for s in self.stackable.get(0,Tk.END)]

	def get_unstackable(self):
		'''Returns a list of file names from the left listbox'''
	
		return [s.join(('SDSS_','.fits')) for s in self.unstackable.get(0,Tk.END)]

	def see_item(self, file_name):
		'''Finds the file name in one of the listboxes
		and jumps to it'''

		search = self.com.search(file_name)
		if search:
			result = search.group()
			stack = self.stackable.get(0,Tk.END)
			unstack = self.unstackable.get(0,Tk.END)
			if result in stack:
				index = stack.index(result)
				self.stackable.see(index)
				self.stackable.selection_clear(0, Tk.END)
				self.stackable.selection_set(index)
				self.stackable.activate(index)
			elif result in unstack:
				index = unstack.index(result)
				self.unstackable.see(index)
				self.unstackable.selection_clear(0, Tk.END)
				self.unstackable.selection_set(index)
				self.unstackable.activate(index)

	def test_click_select(self, event):

		if self.master.canvas_lock_var.get():
			return
		elif event.type == '4': #Click
			selection = event.widget.nearest(event.y)
			item = event.widget.get(selection)
		elif event.type == '2': #Keyboard
			return event.widget.event_generate('<<SingleSelect>>', when = 'tail')
		elif event.type == '35': #Virtual Event
			item = event.widget.get(Tk.ACTIVE)
		if item != self.master.files[self.master.pos][5:-5] and item:
			item = item.join(('SDSS_','.fits'))
			try:
				index = self.master.files.index(item)
				self.master.pos = index
				self.master.view_current(False)
			except IndexError as e:
				print 'IndexError:',e
				#TODO: Fix the program here	
				#Update the listboxes with the correct files

	def on_right_click(self, event):
		"""Add Options Menu"""	
		pass
	
class ImageViewer(Tk.Frame): #Main Interface and Image Viewer
	'''Main interface and image viewer.
	
	Contains all major widgets responsible for viewing the images'''

	def __init__(self, master):
		global current_files

		Tk.Frame.__init__(self, master)
		current_files = os.listdir(IMAGE_PATH)
		self.files = current_files 
		self.median = [] #Place to store the median stack result
		self.pos = 0 #Position in the list of files
		self.canvas_lock_var = Tk.IntVar() #Are we updating the canvas?
		self.createWidgets()
		self.createImage()
		self.packWidgets()
		self.setup_dialog()
		self.update()

	def createImage(self): #Build the canvas and display the first image

		self.ax = self.fig.add_subplot(111)
		#Draw the first image to initialize the display
		self.ax.imshow([[0.0,0.0],[0.0,0.0]], cmap = CMAP, interpolation = 'none')
		self.image = self.ax.images[0] #The image artist
		self.cbar = self.fig.colorbar(self.image, cmap = CMAP, ax = self.ax, orientation = 'vertical', fraction = 0.046, pad = 0.04) #The colorbar artist

		#Set the tick formatter
		ext = IMAGE_SIZE/2.0
		self.image.set_extent((-ext,ext,-ext,ext))
		func = lambda x, pos: '$%i\'\ ^{%s}$' % (x, '{:.4g}'.format(abs(x - int(x))*60.0)+'\'\'' if abs(x - int(x)) > 1e-12 else '')
		formatter = matplotlib.ticker.FuncFormatter(func) 
		self.ax.xaxis.set_major_formatter(formatter)
		self.ax.yaxis.set_major_formatter(formatter)
		func_cbar = lambda x, pos: '$%s$' % (x*1e3)	
		self.cbar.formatter = matplotlib.ticker.FuncFormatter(func_cbar)
		self.cbar.update_ticks()
	
		self.fig.tight_layout()
		self.fig.canvas.draw()
		self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
		if self.files: self.view_current()	

	def createFigure(self):
		'''Build the main figure canvas and toolbar.'''

		self.figureFrame = Tk.Frame(self)
		self.fig = figure(figsize = (7,6), dpi = 100)
		self.canvas = FigureCanvasTkAgg(self.fig, master = self.figureFrame)
		self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.figureFrame)
		self.toolbar.update()

	def createWidgets(self):

		self.createFigure()
		self.stacker = Stacker(self)
		self.buttonFrame = Tk.Frame(self.stacker.buttonFrame)
		self.loaderFrame = Tk.Frame(self)
		self.entryFrame = Tk.Frame(self.stacker.buttonFrame)
		self.next_button = Tk.Button(self.stacker.buttonFrame,text = 'Next', command = self.next)
		self.prev_button = Tk.Button(self.stacker.buttonFrame,text = 'Prev', command = self.prev)
		self.medButton = Tk.Button(self.stacker.buttonFrame, text = 'Median Stack', command = lambda x=None: self.median_stack(self.stacker.get_stackable()))
		self.SmedButton = Tk.Button(self.stacker.buttonFrame, text = 'Smart Median Stack', command = lambda x=None: self.smart_median_stack(self.stacker.get_stackable()))

		self.loader = Tk.Canvas(self.loaderFrame, height = 10) 
		self.canvas_lock = Tk.Checkbutton(self.stacker.descriptionFrame, indicatoron = False, text = 'Lock Canvas', variable = self.canvas_lock_var, padx = 5, pady = 5) 
		self.stats = Tk.Button(self.buttonFrame, text = SIGMA, command = self.get_stats)
			
		self.RA_entry = Tk.Entry(self.entryFrame)
		self.RA_label = Tk.Label(self.entryFrame, text = 'RA:', padx = 5)
		self.DEC_entry = Tk.Entry(self.entryFrame)
		self.DEC_label = Tk.Label(self.entryFrame, text = 'DEC:', padx = 5)
		self.quick_downloader = Tk.Button(self.entryFrame, text = DOWN_ARROW, command = self.download_from_coords)
		#For downloading a single object
	
		if TKDIAG:
			self.downloader = Tk.Button(self.buttonFrame, text = 'Download', command = self.download_from_file)
			self.image_loader = Tk.Button(self.buttonFrame, text = 'Load Image', command = self.load_cutout_from_file)

	def packWidgets(self):

		self.stacker.pack(side = Tk.LEFT, fill = Tk.Y, expand = 0)
		self.figureFrame.pack(side = Tk.TOP, fill = Tk.BOTH, expand = 1)
		self.entryFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)
		self.buttonFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)
		self.loaderFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)
                self.canvas.get_tk_widget().pack(fill = Tk.BOTH, expand = 1)
                self.canvas._tkcanvas.pack(fill = Tk.BOTH, expand = 1)
		self.next_button.pack(side = Tk.RIGHT, expand = 1, fill = Tk.X)
		self.prev_button.pack(side = Tk.LEFT, expand = 1, fill = Tk.X)
		self.canvas_lock.pack(side = Tk.RIGHT, expand = 0, fill = Tk.X)
		self.medButton.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)
		self.SmedButton.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)
		self.stats.pack(side = Tk.LEFT, fill = Tk.NONE, expand = 0, anchor = Tk.NW)
		self.RA_label.pack(side = Tk.LEFT, fill = Tk.NONE, expand = 0)
		self.RA_entry.pack(side = Tk.LEFT, fill = Tk.BOTH, expand = 1)
		self.DEC_label.pack(side = Tk.LEFT, fill = Tk.NONE, expand = 0)
		self.DEC_entry.pack(side = Tk.LEFT, fill = Tk.BOTH, expand = 1)
		self.quick_downloader.pack(side = Tk.LEFT, fill = Tk.NONE, expand = 0)	
	
		if TKDIAG:
			self.downloader.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)
			self.image_loader.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)

	def start_loading(self): #Initialize the Loading bar

		self.rect = self.loader.create_rectangle(0,0,0,10, fill = 'green')
		self.loader.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)

	def update_loading(self, percent): #Update the loading bar
	
		self.loader.coords(self.rect, 0,0,percent*self.loader.winfo_width(), 10)
		self.loader.update()

	def fill_fits_info(self, info):
		'''Fills in misc fits file info to the info frame'''
		
		#Headers:
		#layout:
				
	def view_current(self, see = True): 
		'''View the Image at the Current Position

		Optionally, the @see parameter determines if the
		user would like to highlight the item they are viewing'''

		try:
			self.ax.set_title(self.files[self.pos][5:-5])
			img = fits.open('/'.join((IMAGE_PATH,self.files[self.pos])))[0].data
			self.image.set_data(img)
			self.image.autoscale()
			self.fig.canvas.draw()
			if see: self.stacker.see_item(self.files[self.pos])

		except IOError as e: #The fits file could not load correctly
			print e, 
			if REMOVE_FAILED_LOADS:
				print "Removing"
				os.remove("/".join((IMAGE_PATH,self.files.pop(self.pos))))
				self.view_current()
			else:
				print "Cannot Load"	

	def next(self): #Jump to the next image and display it

		self.pos += 1
		self.pos %= len(self.files)
		self.view_current()
	
	def prev(self): #Jump to the previous image and display it
		
		self.pos -= 1-len(self.files)
		self.pos %= len(self.files)
		self.view_current()

	def median_stack(self, files = None): #Function for finding the median all images
		#TODO: Fix memory issues for large data sets 
		if not files: files = self.files

		if list(self.median) and files is self.files: #"I feel like we've done this before..."
			self.ax.set_title('Median Stacking')
			self.image.set_data(self.median)
			self.image.autoscale()
			self.fig.canvas.draw()
			print "Using Old Stacking"
			return

		data = [] #A list of images to be stacked
		len_files = len(files)
		self.start_loading()
		print "Loading Images..."
		for i,f in enumerate(files):
			print f
			if not i%25: self.update_loading(1.0*i/len_files)
			try:
				img_file = fits.open('/'.join((IMAGE_PATH,f)), memmap = MEMMAP)
				img = img_file[0].data
				img_file.close()				
				if img.shape[0] == round(IMAGE_SIZE*500.0/15.0):
					data.append(img)
			except IOError as e:
				print e,
				if REMOVE_FAILED_LOADS:
					print "Removing"	
					n = files.pop(files.index(f))
					os.remove("/".join((IMAGE_PATH,n)))
				else:
					print "Cannot Load"
		self.update_loading(1.0)
		
		try: 
			print "Stacking... This will take a minute or two"
			data = np.nanmedian(data, axis = 0, overwrite_input = True)
			if files is self.files:self.median = data

		except MemoryError:
			print "Warning: Images are too big!"
			print "Cannot Compute Median"
			return
		self.ax.set_title('Median Stacking')
		self.image.set_data(data)
		self.image.autoscale()
		self.loader.pack_forget()
		self.loader.delete(self.rect)
		self.fig.canvas.draw()
		print "Done"

	def smart_median_stack(self, files = None):
		'''Performs median stacking but with a filter

		Filters out objects whose image centers
		don't seem to show much variance from the 
		full image
		'''
		if not files: files = self.files
		len_files = len(files)
		data = []
		self.start_loading()
		pixels = round(IMAGE_SIZE * 500.0/15.0)
		center = pixels/2
		for i,f in enumerate(files):
			if not i%25: self.update_loading(1.0*i/len_files)
			try:
				img_file = fits.open('/'.join((IMAGE_PATH,f)), memmap = MEMMAP)
				img = img_file[0].data
				img_file.close()				
				if img.shape[0] == pixels:
					std = img.std()
					mean = np.mean(img[center-3:center+3, center-3:center+3])
					full_mean = np.mean(img)
					if mean > full_mean + std:	
						data.append(f)
			except IOError as e:
				print e,
				if REMOVE_FAILED_LOADS:
					print "Removing"	
					n = files.pop(files.index(f))
					os.remove("/".join((IMAGE_PATH,n)))
				else:
					print "Cannot Load"
		self.update_loading(1.0)
		
		self.loader.pack_forget()
		self.loader.delete(self.rect)
		if not data:
			print "No Good Files"
		else:
			self.median_stack(files = data)

	def download_from_coords(self): #download a cutout typed into the entry box
		global current_files
		RA = self.RA_entry.get() #Assume this exists
		DEC = self.DEC_entry.get() #ditto
		downloadCutouts([(RA, DEC)])
		old_files = set(current_files)
		current_files = os.listdir(IMAGE_PATH)
		self.files = current_files
		new_files = set(current_files) - old_files
		try:
			self.stacker.update_listboxes(*new_files)
		except AttributeError as e:
			pass
		try:
			self.pos = self.files.index(list(new_files)[0])
			self.view_current()
		except IndexError as e:
			print "You appear to already have this"
			pass

	def download_from_file(self): #Allows import of coordinate list
		global current_files

		if TKDIAG:

			file_name = tkFileDialog.askopenfilename(filetypes = [('All Files','.*'),('CSV','.csv'),('Text Files','.txt')], initialdir = '.', parent = self)
			if file_name:

				downloadCutouts(genFromFile(file_name))
				old_files = set(current_files)
				current_files = os.listdir(IMAGE_PATH)
				self.files = current_files
				new_files = set(current_files) - old_files
				try:
					self.stacker.update_listboxes(*new_files)
				except AttributeError as e:
					pass

		else:

			print "Function Not Currently Supported."

	def load_cutout_from_file(self): #Manually select an image file to show
		global current_files
		
		if TKDIAG:
		
			file_name = tkFileDialog.askopenfilename(filetypes = [('FITS',('.fits','.fit')), ('All Files','.*')], initialdir = IMAGE_PATH, parent = self)
			while file_name: #Only max 2 loops

				try: #Do we already have this file?
					self.pos = self.files.index(os.path.basename(file_name))
					self.stacker.update_listboxes(file_name)
					self.view_current()
					file_name = ''
				except ValueError as e:
					print e
					print "File Not in",IMAGE_PATH
					#decision = raw_input("Would You Like To Copy it There? (y/N):")
					decision = 'Y'
					if decision.upper() == 'Y':
						shutil.copy(file_name, IMAGE_PATH)
						self.files = current_files = os.listdir(IMAGE_PATH)
						file_name = os.path.basename(file_name)

					else:
						file_name = ''
			
		else:
	
			print "Function Not Currently Supported"
		print "Done"

	def get_stats(self):
		'''Display various statistics about the image
		in a small popup window'''


		data = self.image.get_array()
		std = str(data.std())
		var = str(data.std()**2)
		mean = str(data.mean())
		median = str(np.median(data))
		shape = 'px x '.join(map(str,data.shape))+'px'
		minimum = str(data.min())
		maximum = str(data.max())	
		stat_names = "Mean Min Max Median SD Var Shape".split()
		stat_values = [mean, minimum, maximum, median, std, var, shape]
		stats = zip(stat_names, stat_values)
		text = '\n\n'.join(['{0:<7} {1}'.format(*stat) for stat in stats])

		msgbox = Tk.Toplevel()
		msgbox.title("Statistics")
		msg = Tk.Label(msgbox, text = text, state = Tk.ACTIVE, justify = Tk.LEFT, padx = 5, pady = 5)
		msg.pack(expand = 1, fill = Tk.BOTH)

	def setup_dialog(self):
		'''Optional Standard out and error redirect to Interface'''

		self.err_dlog = Tk.Text(self.stacker.infoFrame, width = 40, bg = 'grey', state = Tk.DISABLED) #The dialog that is redirected to
		def dlog_write(x): #Method for overriding the stdout write
			self.err_dlog.config(state = Tk.NORMAL)
			if x == '\n': x = x + '> '
			self.err_dlog.insert(Tk.END, x)
			self.err_dlog.see(Tk.END)
			self.err_dlog.config(state = Tk.DISABLED)
		self.err_dlog.write = dlog_write
		sys.stdout = self.err_dlog	
		sys.stderr = self.err_dlog	
		self.err_dlog.pack(expand = 1, fill = Tk.BOTH)

def main():

	if len(sys.argv) > 1:
		file_name = sys.argv[1]
		if os.path.isfile(file_name):
			downloadCutouts(genFromFile(file_name))
		else:
			print "Invalid File Name:", file_name
			sys.exit(2)

	root = Tk.Tk()
	root.title("FIRST Image Cutout Tool")
	root.protocol('WM_DELETE_WINDOW', root.quit)
	main = ImageViewer(root)
	main.pack(expand = 1, fill = Tk.BOTH)
	root.mainloop()

if __name__ == '__main__':

	main()

__author__ = "John (Jack) T. O'Brien"
__copyright__ = "Copyright (c) 2015, John O'Brien"
__credits__ = ["Gordon Richards","R.H. Becker","R.L White","D.J. Helfand","Continuum Analytics"]

__version__ = "1.0.4"
__maintainer__ = "John O'Brien"
__email__ = "jto33@drexel.edu"
__date__ = "March 29, 2016"

__since__ = "August 05, 2015"



