from upload import UploadClient
import sys
dl = UploadClient('')
base = '/data/Movies/'
dir = sys.argv[1]

print(dl.new_name(dir))
