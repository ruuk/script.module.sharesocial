def deobfuscate(data):
	import binascii  # @UnusedImport
	return binascii.a2b_base64(binascii.unhexlify(data))