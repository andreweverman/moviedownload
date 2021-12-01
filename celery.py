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
import subprocess

from celery import Celery


print("Running")
broker_url = 'amqp://guest:guest@localhost:5672'
app = Celery('moviedownload',broker=broker_url)
upload_dir = os.getenv("UPLOAD_DIR")
vvn1_client = VVN1MongoClient()
vvn1_client.reset_status_on_start()

@app.on_after_configure.connect
def setup_periodic_tasks(sender):
    sender.add_periodic_task(10.0,download.s(),name='download')
    sender.add_periodic_task(10.0,upload.s(),name='upload')
    sender.add_periodic_task(10.0,delete.s(),name='delete')
    sender.add_periodic_task(10.0,movie_list.s(),name='movielist')

@app.task
def download():
    vvn1_client = VVN1MongoClient()

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

@app.task
def upload():

    vvn1_client = VVN1MongoClient()

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
    
    
@app.task
def delete():

    vvn1_client = VVN1MongoClient()

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



@app.task
def movie_list():

    vvn1_client = VVN1MongoClient()

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

