from pymongo import MongoClient
from bson import ObjectId
import os
import datetime

mongo_uri: str = os.getenv("MONGO_URI")
if not mongo_uri:
    print("Must set MONGO_URI in .env")
    exit(1)



class VVN1MongoClient:

    def __init__(self):
        self.mongo_client = MongoClient(mongo_uri,)
        self.db = self.mongo_client['v2']
        self.guilds = self.db['guilds']

        self.base = 'movie.downloads'
        
        self.element = '.$.'
        self.download_queue='%s.downloadQueue' %self.base
        self.download_queue_element = self.download_queue+self.element

        self.upload_queue='%s.uploadQueue' %self.base
        self.upload_queue_element = self.upload_queue+self.element


        self.uploaded_queue='%s.uploadedQueue' %self.base
        self.uploaded_queue_element = self.uploaded_queue+self.element

        self.status_update = '%s.statusUpdate' %self.base
        self.status_update_element = self.status_update+self.element

        self.in_progress = 'inProgress' 
        self.completed = 'completed' 
        self.percent = 'percent' 
        self.time='time'
        self.status_update_id ='statusUpdateID'
        self.user_id = 'userID' 
        self.text_channel_id = 'textChannelID'
        self.zip_path = 'zipPath'
        self.zip_password = 'zipPassword'
        self.movie_name = 'movieName'
        self.upload_link = 'uploadLink'
        self.upload_path = 'uploadPath'

        self.DOWNLOADING = 'DOWNLOADING'
        self.UPLOADING='UPLOADING'
        self.UPLOADED='UPLOADED'
        self.ERROR='ERROR'

        self.arr_map={self.DOWNLOADING:self.download_queue,self.UPLOADING:self.upload_queue,self.UPLOADED:self.uploaded_queue,self.ERROR:'1'}

    def create_status_update_obj(self,guild_id,_id,status,userID,textChannelID):
        obj = {}
        obj['_id'] = ObjectId()
        obj['started'] = False
        obj['status'] = status
        obj['userID'] = userID
        obj['textChannelID'] = textChannelID

        arr_path = self.arr_map.get(status)

        self.guilds.update_one(
            self.match_status(guild_id,_id,status),
            {'$push': {self.status_update:obj},
            '$set':{arr_path+self.element+self.status_update_id:obj['_id']}}
        )
        return obj['_id']

    def match_status(self,guild_id,_id,status):
        obj = self.match_guild(guild_id)
        obj[self.arr_map[status]+'._id']=_id
        return obj

    def match_status_update(self,guild_id,_id,):
        obj = self.match_guild(guild_id)
        obj['movie.downloads.statusUpdate._id']=_id
        return obj

    def match_guild(self, guild_id)->set:
        return {'guild_id': guild_id}

    def match_download_req(self, guild_id, movie):
        obj = self.match_guild(guild_id)
        obj['movie.downloads.downloadQueue._id']=movie['_id']
        return obj

    def match_upload_req(self, guild_id, movie):
        obj = self.match_guild(guild_id)
        obj['movie.downloads.uploadQueue._id']=movie['_id']
        return obj
    

    def get_list_update(self):
        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.movie_list.awaiting_update':True}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'movie_list': guild_doc['movie']['movie_list']}
        else:
            res = None
        return res

    def get_upload_from_archive(self):
        guild_doc = self.guilds.find_one(
            {'$and':[{'config.premium': True}, {'movie.movie_list.uploadQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'movie_list': guild_doc['movie']['movie_list']}
        else:
            res = None
        return res

    

    def get_download_reqs(self):
        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.downloads.downloadQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'downloads_doc': guild_doc['movie']['downloads']['downloadQueue']}
        else:
            res = None
        return res

    def get_upload_reqs(self):
        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.downloads.uploadQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'uploads_doc': guild_doc['movie']['downloads']['uploadQueue']}
        else:
            res = None
        return res

    def get_uploaded(self):
        guild_doc = self.guilds.find_one(
            {'$and': [{'config.premium': True}, {'movie.downloads.uploadedQueue': {'$not': {'$size': 0}}}]})

        if guild_doc:
            res = {'guild_id': guild_doc['guild_id'],
                   'uploaded_doc': guild_doc['movie']['downloads']['uploadedQueue']}
        else:
            res = None
        return res

    def update_upload_deleted(self,guild_id,id):
        return self.guilds.update_one(self.match_guild(guild_id),
        {'$pull':{self.uploaded_queue:{'_id':id}}})

    def update_downloading_status(self, guild_id, movie, status):
        return self.guilds.update_one(self.match_download_req(guild_id, movie), {
            '$set': {
                self.download_queue_element+ self.in_progress: status}})

   
    def update_uploading_status(self, guild_id, movie, status):
        self.guilds.update_one(self.match_upload_req(guild_id, movie), {
            '$set': {
                self.upload_queue_element+ self.in_progress: status}})

        return self.guilds.update_one(self.match_status_update(guild_id,movie[self.status_update_id]),
            {'$set':{self.status_update_element + 'status' :self.UPLOADING}}
            )
        
   
   

    def download_successful(self, guild_id,  movie,final_dir):
        self.delete_download_element(guild_id, movie)
        self.create_upload_element(guild_id,  movie,final_dir)
    
    def upload_successful(self, guild_id,movie,link,upload_path):        
        return self.guilds.update_one(
            self.match_upload_req(guild_id, movie),
            {'$set':
            {self.upload_queue_element+self.completed:True,
            self.upload_queue_element + self.in_progress:False,
            self.upload_queue_element + self.upload_link:link ,
            self.upload_queue_element + self.upload_path :upload_path}
            }
            

        )

    def delete_download_element(self, guild_id, movie):
        return self.guilds.update_one(
            self.match_download_req(guild_id, movie),
            {'$pull':{self.download_queue:{'_id':movie['_id']}}}
        )
        
    def create_upload_element(self, guild_id, movie,final_dir):
        obj = {}

        obj[self.in_progress] = False
        obj[self.completed] = False
        obj[self.user_id] = movie[self.user_id]
        obj[self.text_channel_id] = movie[self.text_channel_id]
        obj[self.movie_name] = movie[self.movie_name]
        obj[self.zip_path] = final_dir
        obj[self.percent] = 0
        obj[self.time] = 0
        obj['_id'] = ObjectId()
        obj[self.status_update_id] = movie[self.status_update_id]

        return self.guilds.update_one(
            self.match_guild(guild_id),
            {'$push':{self.upload_queue:obj}}
        )

    def add_path_to_drq(self,guild_id,movie,path):
        return self.guilds.update_one(
            self.match_download_req(guild_id, movie),
            {'$set':{self.download_queue_element + 'path':path}}
        )


    def move_to_error(self, guild_id, movie):
        pass
    

    def update_percent(self, guild_id,status, movie, progress, time):
        arr_path = self.arr_map.get(status)

        return self.guilds.update_one(
            self.match_status(guild_id,movie['_id'],status),
            {'$set': {
                arr_path+self.element+self.percent: progress,
                arr_path+self.element+self.time: time,
            }}
        )

    def update_upload_progress(self, guild_id, movie, progress, time):
        return self.guilds.update_one(
            self.match_download_req(guild_id, movie),
            {'$set': {
                self.upload_percent: progress,
                self.seconds_uploading: time,
            }}
        )

    def set_upload_link(self, guild_id, movie,uploadLink):
        return self.guilds.update_one(
            self.match_download_req(guild_id,movie),
            {'$set': {
                self.upload_link: uploadLink}
             }
        )

    def remove_zip_name(self, guild_id, zip_name):
        return self.guilds.update_one({'guild_id': guild_id}, {'$pull': {'movie.downloads.deleteQueue': zip_name}})


    def update_movie_list(self,guild_id,movies):
        return self.guilds.update_one({'guild_id': guild_id},{
            '$set':{
                self.movie_list_movies:movies,
                self.movie_list_awaiting_update:False,
                self.movie_list_last_updated: datetime.datetime.utcnow()}
        })

    
        
        