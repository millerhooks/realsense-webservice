import pyrealsense2 as rs
import numpy as np
import cv2
from flask import *
import json

app = Flask(__name__)

@app.route('/startStream')
def startStream():
	return Response(generateStream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generateStream():
	while (True):
		frames = pipeline.wait_for_frames()
		color_frame = frames.get_color_frame()
		color_image = np.asanyarray(color_frame.get_data())
		data = cv2.imencode('.jpg', color_image)[1].tobytes()

		# To show the stream in a window of server
		'''
		nparr = np.fromstring(data, np.uint8)
		frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
		cv2.imshow('LiveStream', frame)
		cv2.waitKey(1)
		'''
		
		yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n\r\n')

@app.route('/getDepth')
def getDepth():
	x=int(request.args.get('x'))
	y=int(request.args.get('y'))

	# Tested using Intel RealSense D435
	# Change upper bound according to your camera resolution
	if(x>1920 or x<0 or y>1080 or y<0):
		return "Invalid coordinate values"

	# Getting the depth sensor's depth scale (see rs-align example for explanation)
	'''
	depth_sensor = profile.get_device().first_depth_sensor()
	depth_scale = depth_sensor.get_depth_scale()
	'''

	# Create an align object
	# rs.align allows us to perform alignment of depth frames to others frames
	# The "align_to" is the stream type to which we plan to align depth frames.
	align_to = rs.stream.color
	align = rs.align(align_to)

	# Get frameset of color and depth
	frames = pipeline.wait_for_frames()

	# Align the depth frame to color frame
	aligned_frames = align.process(frames)

	# Get aligned frames
	aligned_depth_frame = aligned_frames.get_depth_frame()

	# In metres
	dist_to_center = aligned_depth_frame.get_distance(x,y)
	return str(dist_to_center)
	
@app.route('/getImage')
def getImage():
	return Response(generateImg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get3d')
def get3d():
	x=int(request.args.get('x'))
	y=int(request.args.get('y'))

	# Tested using Intel RealSense D435
	# Change upper bound according to your camera resolution
	if(x>1920 or x<0 or y>1080 or y<0):
		return "Invalid coordinate values"

	align_to = rs.stream.color
	align = rs.align(align_to)

	# Get frameset of color and depth
	frames = pipeline.wait_for_frames()

	# Align the depth frame to color frame
	aligned_frames = align.process(frames)

	# Get aligned frames
	aligned_depth_frame = aligned_frames.get_depth_frame()
	aligned_depth_intrin = aligned_depth_frame.profile.as_video_stream_profile().intrinsics

	depth_pixel = [x, y]
	# In meters
	dist_to_center = aligned_depth_frame.get_distance(x,y)
	pose = rs.rs2_deproject_pixel_to_point(aligned_depth_intrin, depth_pixel, dist_to_center)

	# The (x,y,z) coordinate system of the camera is accordingly
	# Origin is at the centre of the camera
	# Positive x axis is towards right
	# Positive y axis is towards down
	# Positive z axis is into the 2d xy plane

	response = json.dumps({'x': pose[0], 'y': pose[1], 'z': pose[2]})
	return response

def generateImg():
	frames = pipeline.wait_for_frames()
	color_frame = frames.get_color_frame()
	color_image = np.asanyarray(color_frame.get_data())
	data = cv2.imencode('.jpg', color_image)[1].tobytes()
	yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n\r\n')

if __name__ == '__main__':
	pipeline = rs.pipeline()
	cfg = rs.config()
	# The file should be in the same folder as the script
	# Only bag files are compatible, check documentation of RealSense SDK for more information
	cfg.enable_device_from_file("stairs.bag")
	profile = pipeline.start(cfg)
	app.run(host='0.0.0.0')