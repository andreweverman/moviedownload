from upload import UploadClient

dl = UploadClient('')
base = '/data/Movies/'
dir = 'Uncle Boonmee Who Can Recall His Past Lives'

print(dl.new_name(dir))
