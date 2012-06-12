# -*- coding: utf-8 -*-
import os, xbmc
from ShareSocial import Share
from ShareSocial import SHARE_TYPE_IMAGE, SHARE_TYPE_AUDIO, SHARE_TYPE_VIDEO, SHARE_TYPE_LINK, SHARE_TYPE_IMAGEFILE, SHARE_TYPE_VIDEOFILE, SHARE_TYPE_AUDIOFILE, SHARE_TYPE_BINARYFILE, SHARE_TYPE_HTML, SHARE_TYPE_TEXT, SHARE_TYPE_STATUS #@UnusedImport

import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.module.sharesocial')

APILEVEL = 1

MAIN_PATH = xbmc.translatePath(__addon__.getAddonInfo('profile'))
CACHE_PATH = os.path.join(MAIN_PATH,'cache')

if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)

class Clipboard:
	def __init__(self):
		self.clipboard = None
		self.clipFilePath = os.path.join(CACHE_PATH,'CLIPBOARD')
		self.loadCBData()

	def hasData(self,types=None):
		if not self.clipboard: return None
		if types:
			if not self.clipboard.shareType in types: return None
		return self.clipboard.shareType
	
	def getShare(self,source,sharetype):
		return Share(source,sharetype)

	def setClipboard(self,share):
		self.clipboard = share
		self.saveCBData()
	
	def getClipboard(self):
		return self.clipboard
	
	def saveCBData(self):
		if not self.clipboard: return
		data = self.clipboard.toString()
		f = open(self.clipFilePath,'w')
		f.write(data)
		f.close()
		
	def loadCBData(self):
		if not os.path.exists(self.clipFilePath): return
		f = open(self.clipFilePath,'r')
		data = f.read()
		f.close()
		if not data: return
		share = Share().fromString(data)
		self.clipboard = share
		