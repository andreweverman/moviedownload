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

username = os.getenv("MEGA_EMAIL")
password = os.getenv("MEGA_PASSWORD")
ip_addr = os.getenv("TRANSMISSION_IP")
transmission_username = os.getenv("TRANSMISSION_USERNAME")
transmission_password = os.getenv("TRANSMISSION_PASSWORD")
download_dir = os.getenv("DOWNLOAD_DIR")
upload_dir = os.getenv("UPLOAD_DIR")

if not (username and password and ip_addr and download_dir and upload_dir):
    raise Exception('Must set all environment variables: MEGA_EMAIL,MEGA_PASSWORD,TRANSMISSION_IP,MOVIE_DIR')
class DownloadClient:
    def __init__(self,guild_id):
      
        self.torrent_client = Client(
            address=ip_addr,
            username=transmission_username,
            password=transmission_password)

        self.vvn1_mongo_client = VVN1MongoClient()
        self.guild_id=guild_id


    def upload_movie(self, movie_name,zip_name,zip_password):
        # need to zip files and then upload to mega

        self.vvn1_mongo_client.update_uploading_status(self.guild_id,self.movie,True)
        full_hard_drive_path = os.path.join(download_dir,movie_name)                
        hd_zip_name = os.path.join(full_hard_drive_path,zip_name)
        upload_path = upload_dir + zip_name

        subprocess.run(['zip','-j', '-r','--password',zip_password,zip_name,full_hard_drive_path],stdout=subprocess.DEVNULL)
        subprocess.run(['mv', zip_name, hd_zip_name],stdout=subprocess.DEVNULL)
        
        hd_zip_name_f = hd_zip_name.replace(' ', r'\ ')
        upload_command  =  ' '.join(['mega-put',  hd_zip_name_f,upload_path])
        start_time = time.time()    
        percent = 0

        thread = pexpect.spawn(upload_command)
        cpl = thread.compile_pattern_list([pexpect.EOF, '\d+\.\d+\s*%'])
        p_regex = re.compile(r'\d+\.\d+')

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
                        self.vvn1_mongo_client.update_upload_progress(self.guild_id,self.movie,percent,cur_time)
            else:
                output = thread.match.group(0).decode('utf-8')
                print(output)


        # with subprocess.Popen(upload_command,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
        #     for line in p.stdout:
        #         if line.startswith("TRANSFERRING"):
        #             match_percent = re.compile(r':\s*(.*)%').findall(line)
        #             new_percent = int(match_percent[0])                    
        #             cur_time = time.time()-start_time
        #             if(not percent==new_percent):                        
        #                 percent=new_percent
        #                 self.vvn1_mongo_client.update_upload_progress(self.guild_id,self.movie,percent,cur_time)

        match_link = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        get_link_command = ['mega-export', '-a',upload_path]
        with subprocess.Popen(get_link_command,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True) as p:
            for line in p.stdout:
                result = re.findall(match_link,line)                
                if len(result)>0:
                    return result[0]           

        self.vvn1_mongo_client.move_to_error(self.guild_id,self.movie)
      

    def select_movie(self):
        movies = self.get_mega_files()
        movie_str = '\n'.join(["%d: %s" % (i+1, x['a']['n'])
                               for i, x in enumerate(movies)])

        done = False
        movie_i = -1
        while not done:
            try:
                user_input = input("Select a movie\n%s\n" % movie_str)
                movie_i = int(user_input)
                if(movie_i > 0 and movie_i < len(movies)):
                    return movies[movie_i]
            except:
                print("Try again")
        

    def add_movie(self):
        thread = threading.Thread(target=self.download_and_upload)
        thread.start()

    def pia_sys_conn_check(self):

        popen = subprocess.Popen(['piactl','get','connectionstate'],stdout=subprocess.PIPE)
        return popen.communicate()[0].strip().decode('utf-8')

    def check_pia(self):
        sp_res = self.pia_sys_conn_check()        
        if (sp_res =='Connected'):
            return True
        else:
            i = 0
            while i<5:
                subprocess.run('piactl connect') 
                time.sleep(1)
                sp_res = self.pia_sys_conn_check()        
                if(sp_res=='Connected'):
                    return True
        return False

    def download_and_upload(self,movie_obj):
        self.movie = movie_obj
        torrent_url= movie_obj['torrentLink']
        zip_name = movie_obj['zipName']
        zip_password = movie_obj['zipPassword']

        pia_conn =self.check_pia()
        if(not pia_conn):
            return 'Not connected to VPN. Quitting...'
        movie_dir_name = self.download_torrent(torrent_url)

        self.vvn1_mongo_client.download_successful(self.guild_id,self.movie)
        link =self.upload_movie(movie_dir_name,zip_name,zip_password)        
        self.vvn1_mongo_client.set_upload_link(self.guild_id,self.movie,link)  
        self.remove_torrents()

    def filter_torrent_by_hash(self,t_hash:str,torrents=None):
        tor_check= torrents if torrents!=None else self.get_current_torrents()
        
        for tor in tor_check:
            if tor.hash_string == t_hash:
                return tor
        return None


    def download_torrent(self,torrent_url) -> str:

        response = self.add_torrent(torrent_url)
        if(not response.result == 'success'):
            raise Exception('Torrent add failed')

        t_hash: str = ''
        if(response.arguments.torrent_added != None):
            t_hash = response.arguments.torrent_added.hash_string
        elif(response.arguments.torrent_duplicate != None):
            t_hash = response.arguments.torrent_duplicate.hash_string

        downloaded = False
        
        print('\n')
        start_time= time.time()
        while(not downloaded):
            torrent=None
            torrent = self.filter_torrent_by_hash(t_hash)
            if not torrent:
                raise Exception('No torrent found')
            cur_time = int(time.time()-start_time)
            self.vvn1_mongo_client.update_percent(self.guild_id,self.movie,round(torrent.percent_done*100,1),cur_time)
            time.sleep(1)

            if(torrent.percent_done==1):
                downloaded=True
                return torrent.name

            if(cur_time > 200 and torrent.percent_done==0):
                self.vvn1_mongo_client.download_error(self.guild_id,self.movie)
                raise 'Error downloading'
                

    def add_torrent(self,torrent_url):
        try:
    
            download_args: TorrentAddArguments = {
                "filename": torrent_url,
                "download_dir": download_dir
            }

            response: Response[TorrentAdd] = self.torrent_client.torrent.add(
                download_args)
            return response
            
        except Exception as exp:
            raise Exception('Error adding torrent. Check the that was provided url')

    def get_current_torrents(self) -> list:
        response = self.torrent_client.torrent.accessor(all_fields=True)

        torrents = response.arguments.torrents
        return torrents

    def remove_torrents(self):
        torrents = self.get_current_torrents()
        torrents_len = len(torrents)
        if(torrents_len< 1):
            pass
        else:
            [self.torrent_client.torrent.remove(
                torrent.id, False) for torrent in torrents]


'''
TODO:   
    prompt for a movie to delete if no room to add 

'''
