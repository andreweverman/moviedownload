from pymongo import MongoClient
import os

mongo_uri: str = os.getenv("MONGO_URI")
if not mongo_uri:
    print("Must set MONGO_URI in .env")
    exit(1)


class VVN1MongoClient:

    def __init__(self):
        self.mongo_client = MongoClient(mongo_uri,)
        self.db = self.mongo_client['vvn1']
        self.guilds = self.db['guilds']

        self.download_queue_element = 'movie.downloads.downloadQueue.$.'
        self.downloading = "%sdownloading" % self.download_queue_element
        self.downloaded = '%sdownloaded' % self.download_queue_element
        self.download_percent = '%sdownloadPercent' % self.download_queue_element
        self.seconds_downloading = '%ssecondsDownloading' % self.download_queue_element
        self.error = '%serror' % self.download_queue_element
        self.upload_link = '%suploadLink' % self.download_queue_element
        self.uploaded = '%suploaded' % self.download_queue_element
        self.uploading = '%suploading' % self.download_queue_element
        self.upload_percent = '%suploadPercent' % self.download_queue_element
        self.seconds_uploading = '%ssecondsUploading' % self.download_queue_element

    def match_guild(self, guild_id)->set:
        return {'guild_id': guild_id}

    def match_movie(self, guild_id, movie):
        obj = self.match_guild(guild_id)
        obj['movie.downloads.downloadQueue._id']=movie['_id']
        return obj

    def get_new_download_request_doc(self):
        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.downloads.downloadQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'downloads_doc': guild_doc['movie']['downloads']}
        else:
            res = None
        return res

    def get_delete_zip_names(self):

        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.downloads.deleteQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'downloads_doc': guild_doc['movie']['downloads']}
        else:
            res = None
        return res

    def update_downloading_status(self, guild_id, movie, status):
        return self.guilds.update_one(self.match_movie(guild_id, movie), {
            '$set': {
                self.downloading: status}})

    def update_uploading_status(self, guild_id, movie, status):
        return self.guilds.update_one(self.match_movie(guild_id, movie), {
            '$set': {
                self.uploading: status}})

    def upload_successful(self, guild_id, movie):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.uploaded: True,                
                self.uploading: False,
                self.error: False,
            }}
        )

    def download_successful(self, guild_id, movie):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.downloaded: True,
                self.downloading: False,
                self.error: False,
            }}
        )
    def download_error(self, guild_id, movie):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.downloading: False,
                self.downloaded: False,
                self.error: True,
            }}
        )
    def upload_error(self, guild_id, movie):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.uploading: False,
                self.uploaded: False,
                self.error: True,
            }}
        )

    def update_download_progress(self, guild_id, movie, progress, time):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.download_percent: progress,
                self.seconds_downloading: time,
            }}
        )

    def update_upload_progress(self, guild_id, movie, progress, time):
        return self.guilds.update_one(
            self.match_movie(guild_id, movie),
            {'$set': {
                self.upload_percent: progress,
                self.seconds_uploading: time,
            }}
        )

    def set_upload_link(self, guild_id, movie,uploadLink):
        return self.guilds.update_one(
            self.match_movie(guild_id,movie),
            {'$set': {
                self.upload_link: uploadLink}
             }
        )

    def remove_zip_name(self, guild_id, zip_name):
        return self.guilds.update_one({'guild_id': guild_id}, {'$pull': {'movie.downloads.deleteQueue': zip_name}})
