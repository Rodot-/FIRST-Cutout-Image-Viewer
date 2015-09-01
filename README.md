README.md

#FIRST Image Cutout Viewing Tool.
======
The purpose of this tool is to easily extract, view, and manipulate image cutouts from the VLA Faint Images of the Radio Sky at Twenty centimeters (FIRST) survey.  The following information will give a brief overview of how to use this tool to obtain, view, and manipulate these images.


##Downloading Image Cutouts

Downloading a number of image cutouts with this tool is easy.  All that you need is a text file containing a list of object coordinates.  The format of this file should be two columns, separated by a comma with the first column being the angle of right ascension, and the second being the angle of declination on the sky.  Each new object should be separated by a new line.  These coordinates may be formatted in any of the following ways:

     HH MM SS, +-DD MM SS
     HH:MM:SS, +-DD:MM:SS
     HHhMMmSSs, +-DDdMMmSSs
     Decimal Degrees, +-Decimal Degrees
     
In order to extract the objects in your file, simply click the *Download* button and select your file from the browser.  The downloader will start, printing out "Done" when all downloads are complete.  The interface will not be usable while downloading is in progress and you may experience graphical errors.  These will resolve once the download completes.

##Viewing Images

There are multiple ways to view images with this tool.  The first and easiest way is to simply click on the object name in either listbox to view it on the canvas.  Any time a new item in a listbox is selected, the canvas will update with that object.  If you wish to prevent the canvas from updating with changes to listbox selection, you may optionally toggle the *Canvas Lock* button.  This will become useful when analyzing stacked images.

The second way to view an image is with either the *Next* or *Previous* button.  These buttons will display the next image in the program.  This is useful if you wish to keep better track of your place.  As a note, these buttons will always cause the canvas to update, even if the canvas is locked.


##Stacking Images

Stacking Images could not be more straight forward.  To select which images you would like to stack, simply select one or many objects with the cursor or arrow keys in the left listbox and click *Add* to move them to the right listbox.  When either *Median Stack* or *Smart Median Stack* are clicked, the program will use these objects.  If no objects are in the right listbox, the program will stack all objects.  To remove objects, select the objects in the left listbox that you would like to remove and click *Remove*.

There are two methods of median stacking provided by this program.  The simple method which can be run by clicking the *Median Stack* button simply takes the median image of all image cutouts that you wish to stack.  This is most useful if you want to stack a specifically selected group of objects.

The second method is invoked by clicking *Smart Median Stack*.  What this method does differently is that before stacking, it will go through the images and attempt to find images in which there appears to be a bright area in the center.  It will then stack only these images.  This is useful if you have a massive list of images and wish to stack only images that appear to have a visible object near the center.

##Program Configuration

This program has various configuration options that may be edited by editing the python file.  Here I'll list a few of these options and explain what they do.

- IMAGE\_PATH: The directory in which you wish to store image cutouts

- CMAP: The matplotlib colormap you wish to use

- MEMMAP: Numpy memory mapping for fits files

- REMOVE\_FAILED\_LOADS: Whether or not files that fail to load should be removed

- IMAGE\_SIZE: The size of the image in arc-minutes of the cutouts you wish to download.




