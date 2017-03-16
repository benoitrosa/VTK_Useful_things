import os
from natsort import natsorted


class grabVideo:
	"""
	grabVideo is a simple class that will list all jpg files in a folder, sort them by natural order (i.e. 1 2 3 4 .. 10, and not 1 10 2 3 4 ...) and store the result

	when getNextFile is queried, it will return the path to the next image file in the list. It loops when arriving at the end.
	"""

	def __init__(self, path):
		self.folder = path
		self.files = []
		for file in os.listdir(self.folder):
			if file.endswith(".jpg"):
				self.files.append(file)

		self.files = natsorted(self.files)
		self.idx = 0

		
	def getNextFile(self): 
		self.idx += 1
		if (self.idx > len(self.files)):
			self.idx = 0
		return os.path.join(self.folder, self.files[self.idx])
		
