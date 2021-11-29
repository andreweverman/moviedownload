# need to now make this pull from mongo as we will have issues doing actual http request
# ida is now that the download function will post to mongo the params that we were going to do before
# on this app, I will check mongo every 30 seconds if there are any movie download requests.
# DO NOT PULL WHEN DOWNLOADING A MOVIE. only want to do one at a time.
# we then run the download method
#   i could make it to where the movie_download code is looking at a collection for
from dotenv import load_dotenv
load_dotenv()
import os
from mongo_util import VVN1MongoClient
from controller import Controller
import time
import subprocess

print("Running")
upload_dir = os.getenv("UPLOAD_DIR")
def run(first):
    
    vvn1_client = VVN1MongoClient()
    if first:
        vvn1_client.reset_status_on_start()
    download_reqs = vvn1_client.get_download_reqs()

    if download_reqs:
        downloads_doc = download_reqs['downloads_doc']
        guild_id = download_reqs['guild_id']
        for movie in downloads_doc:
            try:
                if not movie['completed'] and not movie['inProgress']:
                    controller = Controller(guild_id)
                    controller.download(movie)
                    break
                elif movie['completed']:
                    vvn1_client.download_successful(guild_id, movie,)
                    pass
            except Exception as e:
                print(e)
                # update the mongo object to have an error in it
                if not e == 'Error downloading':
                    vvn1_client.move_to_error(vvn1_client.DOWNLOADING, guild_id,movie,e)
                pass


    upload_reqs = vvn1_client.get_upload_reqs()
    if upload_reqs:
        uploads_doc = upload_reqs['uploads_doc']
        guild_id = upload_reqs['guild_id']
        for movie in uploads_doc:
            try:
                if not movie['completed'] and not movie['inProgress']:
                    controller = Controller(guild_id)
                    controller.upload(movie)
                    break
                elif movie['completed']:
                    pass
            except Exception as e:
                # update the mongo object to have an error in it
                print(e)
                if not e == 'Error downloading':
                    vvn1_client.move_to_error(vvn1_client.UPLOADING, guild_id,movie,e)
                pass
    
    
    # TODO:fix this shite
    uploaded_docs = vvn1_client.get_uploaded()

    if uploaded_docs:
        doc = uploaded_docs['uploaded_doc']
        guild_id = uploaded_docs['guild_id']
        for movie in doc:
            try:
                if 'removeElement' in movie and movie['removeElement']:
                    upload_path = movie['uploadPath']
                    subprocess.Popen(['mega-rm', upload_path],stdout=subprocess.DEVNULL)
                    vvn1_client.update_upload_deleted(guild_id,movie['_id'])
            except Exception as e:
                pass

    movie_list_update = vvn1_client.get_list_update()
    if movie_list_update:
        try:

            guild_id = movie_list_update['guild_id']
            
            controller = Controller(guild_id)
            movie_list = controller.update_movie_list()
            vvn1_client.update_movie_list(guild_id,movie_list)
        except Exception as e:
            print(e)
            pass


    # res4 = vvn1_client.get_upload_from_archive()
    
    # if res4:
        
    #     movie_list = res4['movie_list']
    #     guild_id = res4['guild_id']
    #     for movie in movie_list['downloadQueue']:
    #         try:
    #             if movie['uploaded'] ==False and movie['error'] ==False:
    #                 download_client = DownloadClient(guild_id)
    #                 vvn1_client.update_downloading_status(guild_id,movie,True)
    #                 download_reqs = download_client.download_and_upload(movie)
    #                 if (res4!=False):
    #                     vvn1_client.upload_successful(guild_id,movie)
    #                 break
    #         except Exception as e:
    #             # update the mongo object to have an error in it
    #             if not e == 'Error downloading':
    #                 vvn1_client.upload_error(guild_id,movie)
    #             pass

run(True)
time.sleep(10)
while True:
    try:
        run(False)
        time.sleep(10)
    except Exception as e:
        print(e)
        print('exception occured')
        time.sleep(100)
