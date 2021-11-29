from download import DownloadClient
from upload import UploadClient


class Controller:

    def __init__(self, guild_id):
        self.guild_id = guild_id

    def download(self, movie_obj):

        dl = DownloadClient(self.guild_id)

        dl_dir = dl.download(movie_obj)


        return dl_dir

    def upload_existing(self, movie_obj):
        ul = UploadClient(self.guild_id)
        ul.upload_existing(movie_obj)


    def upload(self,movie_obj):
        ul = UploadClient(self.guild_id)
        ul.upload(movie_obj)
    
    def update_movie_list(self):
        ul = UploadClient(self.guild_id)
        return ul.get_movie_list()
        
        