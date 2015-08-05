#!/usr/bin/env python
'''
FIRST_cutouts.py
FIRST Image Cutout Viewing Tool
'''
import re, os, urllib2, urllib, socket, sys, itertools
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
if not os.path.exists('FIRST_Cutouts/'):os.makedirs('FIRST_Cutouts/')
#CONSTANTS:
##Program Parameters
REMOVE_FAILED_LOADS = False #Should Incomplete FITS files be removed?
IMAGE_SIZE = 15.0 #Image size in arc-minutes
IMAGE_TYPE = "FITS_File" #Type of image to return
GREEN_POOL_SIZE = 32 #Size of Greenpool: number of concurrent download threads
##Other
#Website we get cutouts from
TARGET = "http://third.ucllnl.org/cgi-bin/firstcutout" #Regular expression for determining the format of input coordinates
COORD_REGEX = "(?P<ms>([+\-]?\d{1,2})(?:(?P<s>[: ])|(?P<f>(?:h|d)))(\d{1,2})(?(f)m|(?P=s))([\d.]+)(?(f)s|\d$))|(?P<deg>^([+\-]?(?=[\d.]).)*$)"
#Regular Expression for generating the object SDSS names
NAME_REGEX = r"(\d{2} \d{2} \d{2}\.\d{2})\d* ([+\-]\d{2} \d{2} \d{2}\.\d)"

#Compile the regex functions
coord_com = re.compile(COORD_REGEX)
name_com = re.compile(NAME_REGEX)

#The list of files already downloaded.  Used to make sure we don't download duplicates
current_files = os.listdir('FIRST_Cutouts/')
#Mutable global variable
#Dictionary of URL parameters to be encoded.  Will be updated for each object
fields = {'RA':"","ImageType":IMAGE_TYPE,"ImageSize":IMAGE_SIZE}
###

def reformat(coord, unit): #Reformats a coordinate based on the units
	result = coord_com.search(coord) #Check if the coordinate is valid
	if result is None: raise Exception("Error: Incorrect Format", coord)
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

def getData(RA,DEC): #Encodes the url data of the RA and DEC for use by getCutout
	coord = " ".join((reformat(RA, 'h'), reformat(DEC, 'deg')))
	name = "SDSS_J"+"".join("".join(name_com.search(coord).groups()).split())+".fits"
	fields['RA'] = coord #fields['RA'] is actually the entire coordinate
	if name not in current_files: #Check if the file is already downloaded
		data = urllib.urlencode(fields)
		return data, name 

def getCutout(data, name): #Downloads the image cutout to a file

	try:
		req = urllib2.Request(TARGET, data)
		resp = urllib2.urlopen(req, None, 10)
		with open('FIRST_Cutouts/'+name,'wb') as f:
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

def genFromFile(file_name): #Generates RA,DEC pairs from a file for use in downloadCutouts

	with open(file_name,'rb') as inFile:
		columns = [row.strip().split(',') for row in inFile]
	return columns

def downloadCutouts(coord_list): #Downloads cutouts from a list of RA, DEC pairs

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

class ImageViewer(Tk.Frame): #Main Interface and Image Viewer

	def __init__(self, master):
		global current_files

		Tk.Frame.__init__(self, master)
		current_files = os.listdir('FIRST_Cutouts/')
		self.files = current_files 
		while not self.files: self.download_from_file()
		self.pos = 0 #Position in the list of files
		self.createWidgets()
		self.createImage()
		self.packWidgets()
		self.update()

	def createImage(self): #Build the canvas and display the first image

		self.ax = self.fig.add_subplot(111)
		#Draw the first image to initialize the display
		self.ax.imshow(fits.open('FIRST_Cutouts/'+self.files[0])[0].data, cmap = 'jet')
		self.image = self.ax.images[0] #The image artist
		#Set the tick formatter
		ext = IMAGE_SIZE/2.0
		self.image.set_extent((-ext,ext,-ext,ext))
		func = lambda x, pos: '$%i\'\ ^{%s}$' % (x, '{:.4g}'.format(abs(x - int(x))*60.0)+'\'\'' if abs(x - int(x)) > 1e-12 else '')
		formatter = matplotlib.ticker.FuncFormatter(func) 
		self.ax.xaxis.set_major_formatter(formatter)
		self.ax.yaxis.set_major_formatter(formatter)
		
		self.fig.canvas.draw()
		self.view_current()	

	def createFigure(self):

		self.figureFrame = Tk.Frame(self)
		self.fig = figure(figsize = (6,6), dpi = 100)
		self.canvas = FigureCanvasTkAgg(self.fig, master = self.figureFrame)
		self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.figureFrame)
		self.toolbar.update()

	def createWidgets(self):

		self.createFigure()
		self.buttonFrame = Tk.Frame(self)
		self.loaderFrame = Tk.Frame(self)
		self.next_button = Tk.Button(self.buttonFrame,text = 'Next', command = self.next)
		self.prev_button = Tk.Button(self.buttonFrame,text = 'Prev', command = self.prev)
		self.medButton = Tk.Button(self.buttonFrame, text = 'Median Stack', command = self.median_stack)

		self.loader = Tk.Canvas(self.loaderFrame, height = 10) 
		if TKDIAG:
			self.downloader = Tk.Button(self.buttonFrame, text = 'Download', command = self.download_from_file)


	def packWidgets(self):

		self.figureFrame.pack(side = Tk.TOP, fill = Tk.BOTH, expand = 1)
		self.buttonFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)
		self.loaderFrame.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)
                self.canvas.get_tk_widget().pack(fill = Tk.BOTH, expand = 1)
                self.canvas._tkcanvas.pack(fill = Tk.BOTH, expand = 1)
		self.next_button.pack(side = Tk.RIGHT, expand = 1, fill = Tk.X)
		self.prev_button.pack(side = Tk.LEFT, expand = 1, fill = Tk.X)
		self.medButton.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)
		if TKDIAG:
			self.downloader.pack(side = Tk.LEFT, fill = Tk.X, expand = 1)

	def start_loading(self): #Initialize the Loading bar

		self.rect = self.loader.create_rectangle(0,0,0,10, fill = 'green')
		self.loader.pack(side = Tk.BOTTOM, fill = Tk.X, expand = 0)

	def update_loading(self, percent): #Update the loading bar
	
		self.loader.coords(self.rect, 0,0,percent*self.loader.winfo_width(), 10)
		self.loader.update()

	def view_current(self): #View the Image at the Current Position
		try:
			self.fig.suptitle(" ".join(self.files[self.pos][:-5].split('_')))
			img = fits.open('FIRST_Cutouts/'+self.files[self.pos])[0].data
			self.image.set_data(img)
			self.image.autoscale()
			self.fig.canvas.draw()

		except IOError as e: #The fits file could not load correctly
			print e, 
			if REMOVE_FAILED_LOADS:
				print "Removing"
				os.remove("FIRST_Cutouts/"+self.files.pop(self.pos))
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

	def median_stack(self): #Function for finding the median all images
		#TODO: Fix memory issues for large data sets 

		data = [] #A list of images to be stacked
		len_files = len(self.files)
		self.start_loading()
		print "Loading Images..."
		for i,f in enumerate(self.files):
			print f
			if not i%100: self.update_loading(1.0*i/len_files)
			try:
				img = fits.open('FIRST_Cutouts/'+f)[0].data
				data.append(img)
			except IOError as e:
				print e,
				if REMOVE_FAILED_LOADS:
					print "Removing"	
					n = self.files.pop(self.files.index(f))
					os.remove("FIRST_Cutouts/"+n)
				else:
					print "Cannot Load"
		self.update_loading(1.0)
		
		try: 
			print "Stacking... This will take a minute or two"
			data = np.nanmedian(data, axis = 0, overwrite_input = True)
		except MemoryError:
			print "Warning: Images are too big!"
			print "Cannot Compute Median"
			return
		self.fig.suptitle('Median Stacking of BAL QSOs')
		self.image.set_data(data)
		self.image.autoscale()
		self.loader.pack_forget()
		self.loader.delete(self.rect)
		self.fig.canvas.draw()

	def download_from_file(self): #Allows import of coordinate list
		global current_files

		if TKDIAG:

			file_name = tkFileDialog.askopenfilename(filetypes = [('All Files','.*'),('CSV','.csv'),('Text Files','.txt')], initialdir = '.', parent = self)
			if file_name:

				downloadCutouts(genFromFile(file_name))
				current_files = os.listdir('FIRST_Cutouts/')
				self.files = current_files

			elif not self.files: sys.exit(2)

		else:

			print "Function Not Currently Supported."


if __name__ == '__main__':

	if len(sys.argv) > 1:
		file_name = sys.argv[1]
		if os.path.isfile(file_name):
			downloadCutouts(genFromFile(file_name))
		else:
			print "Invalid File Name:", file_name
			sys.exit(2)

	root = Tk.Tk()
	root.protocol('WM_DELETE_WINDOW', root.quit)
	main = ImageViewer(root)
	main.pack(expand = 1, fill = Tk.BOTH)
	root.mainloop()


__author__ = "John O'Brien"
__version__ = "1.0.0"
__email__ = "jto33@drexel.edu"
__date__ = "August 05, 2015"
