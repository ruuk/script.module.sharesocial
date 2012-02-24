import os, sys, traceback
import xbmcgui #@UnresolvedImport
from lib import ShareSocial

def LOG(text):
	print 'ShareSocial: share.py: %s' % text

def ERROR(message):
	LOG(message)
	traceback.print_exc()
	return str(sys.exc_info()[1])

def askType():
	options = ('Video','Audio','Image')
	optNames = ('video','audio','image')
	idx = xbmcgui.Dialog().select("Select share type:",options)
	if idx < 0: return None
	return optNames[idx]

def getTypeFromExt(ext):
	if ext in ('avi','mpg','mpeg','asf','mov','mkv','mp4','wmv','rm'):
		return 'videofile'
	elif ext in ('wav','mp3','aif'):
		return 'audiofile'
	elif ext in ('jpg','jpeg','png','tif','bmp','gif'):
		return 'imagefile'
	return None

def getTypeFromFolderPath(path):
	media = path.split('.',2)[:2][-1]
	if media in ('image','video','audio'): return media
	media = path.split('db://',1)[0].replace('music','audio')
	if media in ('image','video','audio'): return media
	return None

def processShare():
	LOG('Processing share')
	
	argNames = ['ignore','apiver','addonID','addonName','ext','imagepath','title','path','label','folderpath']
	args = {}
	
	for s in sys.argv:
		if not argNames: break
		argName = argNames.pop(0)
		args[argName] = s
	
	print 'Test: %s' % args
	print sys.argv
	
	shareType = None
	if args.get('imagepath'):
		shareType = 'imagefile'
		LOG('shareType: %s - determined by PicturePath' % shareType)
	else:
		ext = args.get('ext')
		if ext: shareType = getTypeFromExt(ext)
		if shareType:
			LOG('shareType: %s - determined by FileExtension' % shareType)
		else:
			shareType = getTypeFromFolderPath(args.get('folderpath'))
			if shareType:
				LOG('shareType: %s - determined from FolderPath' % shareType)
			else:
				shareType = askType()
				if shareType:
					LOG('shareType: %s - determined by asking user' % shareType)
				else:
					return
		
	share = ShareSocial.getShare(args['addonID'], shareType)
	share.title = args.get('title',args.get('label',''))
	share.media = args.get('path')
	share.sourceName = args.get('addonName')
	
	if share.shareType in ('imagefile','videofile','audiofile'):
		if share.mediaIsRemote():
			LOG('Share is media and remote.')
			if share.mediaIsWeb():
				LOG('Share is media and on the web. Looking for local copy...')
				path = ShareSocial.getCachedPath(share.media)
				if path:
					LOG('Found cached content')
				else:
					LOG('Not cached - downloading...')
					targetPath = os.path.join(ShareSocial.MAIN_PATH,args.get('label','file'))
					try:
						path = ShareSocial.getFile(share.media, targetPath)
					except:
						ERROR('Download failed!')
					
				if path:
					LOG('Converting content to local file')
					alt = share.getCopy()
					alt.shareType = alt.shareType.replace('file','')
					share.media = path
					share.addAlternate(alt)
				else:
					LOG('Could not download content - changing type to %s' % share.shareType.replace('file',''))
					share.shareType = share.shareType.replace('file','')
			else:
				xbmcgui.Dialog().ok('Failed','Unable to share remote file.')
				return
			
	share.share()

processShare()