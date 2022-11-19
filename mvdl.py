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
from download import DownloadClient

from celery import Celery


print("Running")
broker_url = os.getenv('BROKER_URL')
app = Celery('tasks',broker=broker_url)
upload_dir = os.getenv("UPLOAD_DIR")
vvn1_client = VVN1MongoClient()


# default_exchange = Exchange('default', type='direct')
# movie_add_queue = Queue('addMovie', default_exchange, routing_key='addMovie')

task_routes = {
    'download':{
        'queue':'movie_add_queue',
    }
}
task_protocol = 1

@app.task
def download(request:dict):
    vvn1_client = VVN1MongoClient()

    guild_id = request.get('guildId')
    try:

        dl = DownloadClient(guild_id)

        dl_dir = dl.download(request)

        return dl_dir
    except Exception as e:
        print(e)
