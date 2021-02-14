# need to now make this pull from mongo as we will have issues doing actual http request
# ida is now that the download function will post to mongo the params that we were going to do before
# on this app, I will check mongo every 30 seconds if there are any movie download requests.
# DO NOT PULL WHEN DOWNLOADING A MOVIE. only want to do one at a time.
# we then run the download method
#   i could make it to where the movie_download code is looking at a collection for
from dotenv import load_dotenv
load_dotenv()
import os
from moviedownload import DownloadClient
from mongo_util import VVN1MongoClient
import time

upload_dir = os.getenv("UPLOAD_DIR")
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

def run():
    
    vvn1_client = VVN1MongoClient()
    res = vvn1_client.get_new_download_request_doc()

    if res:
        downloads_doc = res['downloads_doc']
        guild_id = res['guild_id']
        for movie in downloads_doc['downloadQueue']:
            try:

                if movie['uploaded'] ==False:
                    download_client = DownloadClient(guild_id)
                    vvn1_client.update_downloading_status(guild_id,movie,True)
                    download_client.download_and_upload(movie)
                    vvn1_client.upload_successful(guild_id,movie)
                    break

            except Exception as e:
                # update the mongo object to have an error in it
                vvn1_client.upload_error(guild_id,movie)
                pass
    
    res2 = vvn1_client.get_delete_zip_names()

    if res2:
        
        try:
            downloads_doc = res2['downloads_doc']
            guild_id = res2['guild_id']
            for zip_name in downloads_doc['deleteQueue']:
                res = vvn1_client.remove_zip_name(guild_id,zip_name)
                os.remove(os.path.join(upload_dir,zip_name))
        except Exception:
            pass


while True:
    try:
        run()
        time.sleep(10)
    except Exception as e:
        print(e)
        print('exception occured')
        time.sleep(100)