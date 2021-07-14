from download import DownloadClient
from upload import UploadClient


class Controller:

    def __init__(self, guild_id):
        self.guild_id = guild_id

    def download_and_upload(self, movie_obj):

        dl = DownloadClient(self.guild_id)

        dl_dir = dl.download(movie_obj)

        ul = UploadClient(self.guild_id)
        ul.upload(dl_dir, movie_obj)

        return True

    def upload_existing(self, movie_obj):
        ul = UploadClient(self.guild_id)
        ul.upload_existing(movie_obj)
