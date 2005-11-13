import sys

if __name__ == "__main__":
	newPath = "" # New Path
	if len(sys.argv) < 2:
		print "Error: Please specify a system type (unix or win32)"
		sys.exit()
	if sys.argv[1] == "win32":
		seperator = ";"
	elif sys.argv[1] == "unix":
		seperator = ":"
	else:
		print "Error: Unknown system type '%s'" % (argv[1])
		sys.exit()

	for s in range(0, len(sys.path)-1):
        	newPath += "%s%s" % (sys.path[s], seperator)
       	newPath += sys.path[-1]
	print newPath
