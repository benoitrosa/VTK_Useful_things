import os, sys

import vtk
import numpy as np
import cv2
from rotation_matrix import R_2vect
from grabVideo import grabVideo



class vtkTimerCallback():
	"""
	Callback that is used by a VTK timer to update the texture periodically
	"""
	def __init__(self):
		self.timer_count = 0
 
	def execute(self,obj,event):
		self.text.updateImage(self.vid.getNextFile())
		iren = obj
		iren.GetRenderWindow().Render()
		self.timer_count += 1






def StoreAsMatrix4x4(marray):
	"""
	Copies the elements of a numpy array into a vtkMatrix4x4.

	:@type: numpy.ndarray
	:@param matrix: The array to be copied into a matrix.
	:@rtype matrix: vtk.vtkMatrix4x4
	"""
	m = vtk.vtkMatrix4x4()
	for i in range(4):
		for j in range(4):
			m.SetElement(i, j, marray[i,j])
	return m


class tiledTexture():
	"""
	TiledTexture class. Creates a plane with an input image applied on it as a textures

	Using tiles allows to circumvent the subsampling that is performed by VTK when applying a large texture on a plane
	"""

	def __init__(self, imagepath, center = [0,0,0], direction = [0,0,1], kernel = 4):
		"""
		Class initialization

		:@param	imagepath:	path to the source image to be used as a textures
		:@param	center:	coordinates of the center of the plane
		:@param direction:	normal to the plane
		:@param kernel:	number of tiles per row. Will create kernel squared tiles
		"""
		self.path = imagepath
		
		self.sources = []

		self.reader = vtk.vtkJPEGReader()
		self.reader.SetFileName(self.path)
		self.reader.Update()

		self.img = cv2.imread(self.path)
		self.h,self.w = self.img.shape[:2]

		self.VOIs = []
		self.textures = []
		self.textMappers = []
		self.mappers = []
		self.actors = []

		self.center = center
		self.direction = direction

		self.T = np.eye(4)
		R_2vect(self.T,[0,0,1],self.direction)
		self.T[0,3] = self.center[0]
		self.T[1,3] = self.center[1]
		self.T[2,3] = self.center[2]

		self.transform = vtk.vtkTransform()
		self.transform.SetMatrix(StoreAsMatrix4x4(self.T))

		self.createTexture(kernel)

	def updateImage(self,imagepath):
		"""
		Update the image that is used a texture. Useful for animating videos on a given plane

		:@param	imagepath:	path to the source image to be used as a texture
		"""
		self.path = imagepath
		self.reader.SetFileName(imagepath)
		self.img = np.transpose(cv2.imread(self.path))
		self.h,self.w = self.img.shape[:2]

	def createTexture(self, kernel = 4):
		"""
		Create the tiled Texture plane. This method is called in the constructor and should not be called directly

		:@param	kernel:	number of tiles per row. Will create kernel squared tiles
		"""
		# Step should be an integer, and tiles should be its square
		step = int(kernel)
		tiles = int(step*step)

		# Warning if the image size cannot be divided by the step
		if not(int(1.0*self.w/step) - self.w/step == 0) or not (int(1.0*self.h/step) - self.h/step == 0):
			print "Warning: image size not divisible by the number of tiles. May cause problems ..."

		# Generate each tile
		cur_x = 0
		cur_y = 0

		for i in range(tiles):

			# Update tile sub-coordinates
			if i==0:
				cur_x = 0
				cur_y = 0
			elif i%step == 0:	
				cur_x = 0	
				cur_y += self.h/step			
			else:
				cur_x += self.w/step

			# Compute the min-max coordinates of the tile
			xmin = np.max([0,cur_x])
			xmax = np.min([cur_x + self.w/step -1, self.w-1])
			ymin = np.max([0,cur_y])
			ymax = np.min([cur_y + self.h/step -1, self.h-1])
			xmid = (xmin + xmax)/2
			ymid = (ymin + ymax)/2
	
			# Generate a plane with the right dimensions
			source = vtk.vtkPlaneSource()
			source.SetNormal(self.direction[0],self.direction[1],self.direction[2])
			source.SetCenter(xmin,ymin,0)
			source.SetPoint2(xmax+1,ymin-1,0) #-1 and +1 to have minimal overlap between tiles. Suboptimal ...
			source.SetPoint1(xmin-1,ymax+1,0)

			# Extract ROI from image to generate tile texture
			newVOI = [xmin,xmax,ymin,ymax,0,0]
			extractVOI = vtk.vtkExtractVOI()
			extractVOI.SetInputConnection(self.reader.GetOutputPort())
			extractVOI.SetVOI(newVOI)

			# Generate the texture			
			texture = vtk.vtkTexture()
			texture.SetInputConnection(extractVOI.GetOutputPort())

			#Map texture coordinates
			map_to_plane = vtk.vtkTextureMapToPlane()
			map_to_plane.SetInputConnection(source.GetOutputPort())

			# Create mapper and set the mapped texture as input
			mapper = vtk.vtkPolyDataMapper()
			mapper.SetInputConnection(map_to_plane.GetOutputPort())

			# Create actor and set the mapper and the texture
			actor = vtk.vtkActor()
			actor.SetMapper(mapper)
			actor.SetTexture(texture)

			# Rotate the actor to set the plane in the right position/orientation
			actor.SetUserMatrix(self.transform.GetMatrix())

			# Save references to VTK objects in the class for later modifications, if needed
			self.sources.append(source)
			self.VOIs.append(extractVOI)
			self.textures.append(texture)
			self.textMappers.append(map_to_plane)
			self.mappers.append(mapper)
			self.actors.append(actor)


	def getActors(self):
		"""
		Returns the tile actors

		:@rtype	vtkactors
		"""
		return self.actors



if __name__ == '__main__':

	if len(sys.argv) <2:
		print "Please provide the path to the images folder as a CLI argument"
		sys.exit(1)

	path = sys.argv[1]
	print "Grabbing images from: ", path
	
	# imagepath should be a folder containing input images in JPEG format
	vid = grabVideo(path)

	# Create a render window
	ren = vtk.vtkRenderer()
	renWin = vtk.vtkRenderWindow()
	renWin.AddRenderer(ren)
	renWin.SetSize(640,480)
	iren = vtk.vtkRenderWindowInteractor()
	iren.SetRenderWindow(renWin)

	# Create tiledTexture object
	text = tiledTexture(vid.getNextFile(), kernel = 4, direction = [1,2,1])

	# Add actors to the scene
	for actor in text.getActors():
		ren.AddActor(actor)

	iren.Initialize()

	# Create timer to animate texture
	cb = vtkTimerCallback()
	cb.vid = vid
	cb.text = text 
	iren.AddObserver('TimerEvent', cb.execute)
	timerId = iren.CreateRepeatingTimer(10);

	# Start the rendering pipeline
	renWin.Render()
	iren.Start()
