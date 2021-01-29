# need to now make this pull from mongo as we will have issues doing actual http request
# ida is now that the download function will post to mongo the params that we were going to do before
# on this app, I will check mongo every 30 seconds if there are any movie download requests.
# DO NOT PULL WHEN DOWNLOADING A MOVIE. only want to do one at a time.
# we then run the download method
#   i could make it to where the movie_download code is looking at a collection for
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from random import shuffle
from moviedownload import DownloadClient
load_dotenv()
mongo_uri: str = os.getenv("MONGO_URI")
if not mongo_uri:
    print("Must set MONGO_URI in .env")
    exit(1)


'''
movie =>  movie_download_requests

{
    user_id:string
    movie_name:string
    torrent_url:string
    torrent_password:string
    downloaded:boolean
    currently_uploaded:boolean    
    prompt_to_make_room:boolean
}
'''

mongo_client = MongoClient(mongo_uri)
download_client =DownloadClient() 

db = mongo_client['vvn1']


guild_doc = db['guilds'].find_one(
    {'$and': [{'premium': True}, {'movie.downloads': {'$not': {'$size': 0}}}]})

try:

    downloads_doc = guild_doc['movie']['downloads']
    if len(downloads_doc)>0:
        chosen_movie_download = downloads_doc[0]
        download_client.download_and_upload(chosen_movie_download)

except Exception:
    # update the mongo object to have an error in it
    pass
    