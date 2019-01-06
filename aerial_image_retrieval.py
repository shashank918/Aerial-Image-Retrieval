
import argparse
import numpy as np
import requests
import json
import cv2
import urllib

MIN_LAT = -85.05112878
MIN_LONG = -180
MAX_LAT = 85.05112878
MAX_LONG = 180
MAX_RESOLUTION = 23

def clip(n, min_Val, max_Val):
	return min(max(n,min_Val),max_Val)

def gettile_map(latitude, longitude, zoomLevel):
	reqUrl = "http://dev.virtualearth.net/REST/V1/Imagery/Metadata/Aerial/%s,%s?zl=%d&o=json&key=Ar06c1OUpI2J_CqetJaaKjfTaHjaC8ZtnK_cOPDzd6VBkZN2jimQC3Li0_TjmXIq" %(latitude, longitude, zoomLevel)

	response = requests.get(reqUrl)

	data = json.loads(response.text)
	tile_mapUrl = data["resourceSets"][0]["resources"][0]["imageUrl"]


	imageResponse = urllib.urlopen(tile_mapUrl)
	tile_map = np.asarray(bytearray(imageResponse.read()), dtype="uint8")
	tile_map = cv2.imdecode(tile_map, cv2.IMREAD_COLOR)
	return tile_map


def gettile_mapWithQuadKey(quadKey):
	tile_mapUrl = "http://h0.ortho.tiles.virtualearth.net/tiles/h%s.jpeg?g=131" %(str(quadKey))
	imageResponse = urllib.urlopen(tile_mapUrl)
	tile_map = np.asarray(bytearray(imageResponse.read()), dtype="uint8")
	tile_map = cv2.imdecode(tile_map, cv2.IMREAD_COLOR)
	return tile_map

def getTileXY(latitude, longitude, zoomLevel):
	latitude = clip(latitude, MIN_LAT, MAX_LAT)
	longitude = clip(longitude, MIN_LONG, MAX_LONG)

	sinLatitude = np.sin(latitude * np.pi/180)
	levelConstant = 2**zoomLevel
	pixelX = ((longitude + 180) / 360) * 256 * levelConstant
	pixelY = (0.5 - np.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * np.pi)) * 256 * levelConstant
	tileX = int(np.floor(pixelX / 256))
	tileY = int(np.floor(pixelY / 256))
	return tileX, tileY


def getListOfTiles(tile1, tile2):
	tiles = []
	for i in range(tile1[0],tile2[0]+1):
		for j in range(tile1[1],tile2[1]+1):
			tuple = (i, j)
			tiles.append(tuple)
    	return tiles

def getQuadKey(tileX, tileY, zoomLevel):
	quadKey = ''
	for i in range(zoomLevel, 0, -1):
		digit = 0
		mask = 1 << (i-1)
		if tileX & mask != 0:
			digit += 1
		if tileY & mask != 0:
			digit += 2
		quadKey += str(digit)
	return quadKey


def getInitialTileXYList(latitude1, longitude1, latitude2, longitude2):
	zoomLevel = 23
	for itr in range(MAX_RESOLUTION,0,-1):
		sTileX, sTileY = getTileXY(latitude1, longitude1, itr)
		eTileX, eTileY = getTileXY(latitude2, longitude2, itr)

		tile_map3 = gettile_mapWithQuadKey(getQuadKey(sTileX, sTileY, itr))
		tile_map4 = gettile_mapWithQuadKey(getQuadKey(eTileX, eTileY, itr))

		diff = cv2.absdiff(tile_map3,test)
		if int(np.mean(diff)) < 2:
			continue
		else:
			zoomLevel = itr
			break


	tileList = getListOfTiles(min((eTileX,eTileY),(sTileX,sTileY)), max((eTileX,eTileY),(sTileX,sTileY)))
	return tileList, zoomLevel


def getRevisedTileXYList(latitude1, longitude1, latitude2, longitude2, zoomLevel):
	sTileX, sTileY = getTileXY(latitude1, longitude1, zoomLevel)
	eTileX, eTileY = getTileXY(latitude2, longitude2, zoomLevel)

	tileList = getListOfTiles(min((eTileX,eTileY),(sTileX,sTileY)), max((eTileX,eTileY),(sTileX,sTileY)))
	return tileList

def getReqtile_map(tileList):
	global stile_map, etile_map
	startXVal = tileList[0][0]
	endYVal = tileList[-1][1]
	IsFirstTile = True
	colTiles = []
	reqtile_map = []


	if args["release"] == False:
		stile_map = gettile_mapWithQuadKey(getQuadKey(tileList[0][0], tileList[0][1], zoomLevel))
		etile_map = gettile_mapWithQuadKey(getQuadKey(tileList[-1][0], tileList[-1][1], zoomLevel))

	for i in range(0,len(tileList)):
		xVal = tileList[i][0]
		yVal = tileList[i][1]
		if xVal == startXVal and IsFirstTile == True:
			tile_map = gettile_mapWithQuadKey(getQuadKey(xVal, yVal, zoomLevel))
			IsFirstTile = False
			diff = cv2.absdiff(tile_map,test)
			if int(np.mean(diff)) < 2:
				return reqtile_map, "NOT_OK"
		elif xVal == startXVal:
			tile_mapBelow = gettile_mapWithQuadKey(getQuadKey(xVal, yVal, zoomLevel))
			diff = cv2.absdiff(tile_mapBelow,test)
			if int(np.mean(diff)) < 2:
				return reqtile_map, "NOT_OK"
			tile_map = np.concatenate((tile_map,tile_mapBelow),axis = 0)
		if yVal == endYVal:
			colTiles.append(tile_map)
			IsFirstTile = True
			startXVal += 1

	for each in colTiles:
		if IsFirstTile == True:
			reqtile_map = each
			IsFirstTile = False
		else:
			reqtile_map = np.concatenate((reqtile_map,each),axis = 1)


	cv2.imwrite("output.jpeg", reqtile_map)
	reqtile_map = resize_image(reqtile_map,height=512)
	return reqtile_map, "OK"

def resize_image(image, width = None, height = None, inter = cv2.INTER_AREA):

	dim = None
	(ht, wt) = image.shape[:2]


	if width is None and height is None:
		return image

	if width is None:

		ratio = height / float(ht)
		new_dimension = (int(wt * ratio), height)
	else:

		ratio = width / float(wt)
		new_dimension = (width, int(ht * ratio))


	resized = cv2.resize(image, new_dimension, interpolation = inter)
	return resized


if __name__ == "__main__":
	print "** Map Tile Process Begins here **"
	stile_map = []; etile_map = []

	test_input = {"lat1":"40.714550167322159", "long1":"-74.007124900817871", "lat2":"40.715550167322159", "long2":"-74.009124900817871"}


	try:
		ap = argparse.ArgumentParser()
		ap.add_argument("-lt1", "--latitude1", default = test_input["lat1"],
			help = "Latitude1")
		ap.add_argument("-ln1", "--longitude1", default = test_input["long1"],
			help = "Longitude1")
		ap.add_argument("-lt2", "--latitude2", default = test_input["lat2"],
			help = "Latitude2")
		ap.add_argument("-ln2", "--longitude2", default = test_input["long2"],
			help = "Longitude2")
		ap.add_argument("-r", "--release", default = False,
			help = "debug or release mode")

		args = vars(ap.parse_args())
		test = cv2.imread("test.jpeg")

		tileList, zoomLevel = getInitialTileXYList(float(test_input["lat1"]), float(test_input["long1"]), float(test_input["lat2"]), float(test_input["long2"]))

		reqtile_map, statusCode = getReqtile_map(tileList)


		while(statusCode == "NOT_OK"):
			tileList, zoomLevel = getRevisedTileXYList(float(test_input["lat1"]), float(test_input["long1"]), float(test_input["lat2"]),
										float(test_input["long2"]), zoomLevel-1)
			reqtile_map, statusCode = getReqtile_map(tileList)



		cv2.imshow("Requested map tile", reqtile_map)
		cv2.waitKey(0)
	except:
		print "Please input correct values"
