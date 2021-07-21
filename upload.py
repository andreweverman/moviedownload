from shutil import copyfile
from clutch import Client
from requests import Response
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.add import TorrentAdd
import threading
import time
import subprocess
import os
from mongo_util import VVN1MongoClient
import re
import sys
import pexpect
from datetime import datetime

download_dir = os.getenv("DOWNLOAD_DIR")
upload_dir = os.getenv("UPLOAD_DIR")
MAX_MEGA_SIZE = 21474825485

if not (download_dir and upload_dir):
    raise Exception('Must set all environment variables: MEGA_EMAIL,MEGA_PASSWORD,TRANSMISSION_IP,MOVIE_DIR')
class UploadClient:
    def __init__(self,guild_id):
      
        self.vvn1_mongo_client = VVN1MongoClient()
        self.guild_id=guild_id

    def upload_existing(self,movie_obj):
        pass

    def upload(self,movie_obj):
        # need to zip files and then upload to mega
        self.movie = movie_obj
        self.vvn1_mongo_client.update_uploading_status(self.guild_id,self.movie,True)
        hd_zip_path = self.movie['zipPath']
        zip_name = os.path.basename(self.movie['zipPath'])

        if not self.have_room_for_upload(hd_zip_path):
            self.make_room_for_upload(hd_zip_path)

        upload_path = upload_dir + zip_name
        upload_command  =  ' '.join(['mega-put',  hd_zip_path.replace(' ', r'\ '),upload_path])
        start_time = time.time()    
        percent = 0

        thread = pexpect.spawn(upload_command)
        cpl = thread.compile_pattern_list([pexpect.EOF, '\d+\.\d+\s*%'])
        p_regex = re.compile(r'\d+\.\d+')
        
        # updates the percent complete in vvn1.
        while True:
            i = thread.expect_list(cpl,timeout=None)
            if i==0:
                break
            elif i==1:
                output = thread.match.group(0).decode('utf-8')
                matched = re.findall(p_regex,output)                
                new_percent = float(matched[0])                       
                cur_time = int(time.time()-start_time)
                if percent!=new_percent:                        
                        percent=new_percent
                        self.vvn1_mongo_client.update_percent(self.guild_id,self.vvn1_mongo_client.UPLOADING,self.movie,percent,cur_time)
            else:
                output = thread.match.group(0).decode('utf-8')
                print(output)

        # need to get the link for the zip we just uploaded
        match_link = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        get_link_command = ['mega-export', '-a',upload_path]
        with subprocess.Popen(get_link_command,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
            for line in p.stdout:
                result = re.findall(match_link,line)                
                if len(result)>0:
                    self.vvn1_mongo_client.upload_successful(self.guild_id,self.movie,result[0],upload_path)
                    return True

            return False
      

    def get_mega_size(self)-> int:
        matcher = re.compile(r'Total storage used: \s*([\d]*)')
        command = ['mega-du']
        with subprocess.Popen(command,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
            for line in p.stdout:
                result = re.findall(matcher,line)
                if len(result) >0:
                    return int(result[0])
        return -1
    def have_room_for_upload(self,zip_path) -> bool:
        return self.size_after_upload(zip_path) < MAX_MEGA_SIZE

    def size_after_upload(self,zip_path):
        return self.get_mega_size() + os.path.getsize(zip_path)

    def make_room_for_upload(self,zip_path) -> bool:
        size_map = {'MB':100000,'GB':1073741824,'KB':1000}
        uploads = []
        matcher = re.compile(r'(\d+\.\d+)\s*([\w]{2})\s*([\d]{2}[A-Za-z]{3}[\d]{4}\s*[\d]{2}:[\d]{2}:[\d]{2})\s*(.*)')
        command = ['mega-ls','-lh']
        with subprocess.Popen(command,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
            for line in p.stdout:
                r =  re.findall(matcher,line)
                if len(r) > 0:
                    r = list(r[0])
                    upload = {}
                    upload['name'] = r[3]
                    upload['date']=datetime.strptime(r[2] , '%d%b%Y %H:%M:%S')           
                    size = float(r[0])
                    if r[1] in size_map:
                        size *= size_map[r[1]]

                    
                    upload['size'] = size

                    uploads.append(upload)

        sorted_list = sorted(uploads,key = lambda x: x['date'])

        delete = []

        new_size  = self.size_after_upload(zip_path)

        if new_size<MAX_MEGA_SIZE:
            return True

        for u in sorted_list:
            new_size -= u['size']
            delete.append(u)
            if new_size<MAX_MEGA_SIZE:
                break
        
        for u in delete:
            subprocess.Popen(['mega-rm', 'vvn1/%s'%u['name']],stdout=subprocess.DEVNULL)
        
        return True