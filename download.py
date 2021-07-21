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
import shutil

username = os.getenv("MEGA_EMAIL")
password = os.getenv("MEGA_PASSWORD")
ip_addr = os.getenv("TRANSMISSION_IP")
download_dir = os.getenv("DOWNLOAD_DIR")
upload_dir = os.getenv("UPLOAD_DIR")

if not (username and password and ip_addr and download_dir and upload_dir):
    raise Exception(
        'Must set all environment variables: MEGA_EMAIL,MEGA_PASSWORD,TRANSMISSION_IP,MOVIE_DIR')


class DownloadClient:
    def __init__(self, guild_id):

        self.torrent_client = Client(
            address=ip_addr)
        self.vvn1_mongo_client = VVN1MongoClient()
        self.guild_id = guild_id

    def download(self, movie_obj):
        self.movie = movie_obj
        self.vvn1_mongo_client.update_downloading_status(self.guild_id,self.movie,True)
        if not self.vvn1_mongo_client.status_update_id in self.movie:
            self.movie[self.vvn1_mongo_client.status_update_id] = self.vvn1_mongo_client.create_status_update_obj(self.guild_id,self.movie['_id'],self.vvn1_mongo_client.DOWNLOADING,self.movie['userID'],self.movie['textChannelID'])

        torrent_url = movie_obj['torrentLink']

        pia_conn = self.check_pia()
        if(not pia_conn):
            return 'Not connected to VPN. Quitting...'
        movie_dir_name = self.download_torrent(torrent_url)

        if 'path' not in self.movie:
            final_dir = self.fix_dir(movie_dir_name)
        else:
            final_dir = self.movie['path']
        final_dir_formatted = self.zip_movie(final_dir)
        self.vvn1_mongo_client.download_successful(self.guild_id, self.movie,final_dir_formatted)
        self.remove_torrents()
        return final_dir



    def fix_dir(self, outer_dir):

        check_dir = outer_dir
        first= True
        first_sub_dir = ''
        new_outer_name = ''

        while True:

            dirs = [f.path for f in os.scandir(check_dir) if f.is_dir()]            
            files = [f.path for f in os.scandir(check_dir) if not f.is_dir()]

            if len(dirs) == 1 and len(files) ==0:
                if first:
                    first_sub_dir = dirs[0]
                    first=False
                check_dir = dirs[0]
            
            else:
                if not first:
                    new_outer_name = os.path.join(download_dir,os.path.basename(check_dir))
                    file_list = [f.path for f in os.scandir(check_dir)]
                    for f in file_list:
                        shutil.move(f, outer_dir)
                break
                
        if first_sub_dir != '':
            shutil.rmtree(first_sub_dir)
        
        # TODO: can add a prop to the download thing for the dir name in this case

        if not os.path.exists(new_outer_name) and os.path.exists(outer_dir):
            os.rename(outer_dir,new_outer_name)
            self.vvn1_mongo_client.add_path_to_drq(self.guild_id,self.movie,new_outer_name)

        return new_outer_name

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

        popen = subprocess.Popen(
            ['piactl', 'get', 'connectionstate'], stdout=subprocess.PIPE)
        return popen.communicate()[0].strip().decode('utf-8')

    def check_pia(self):
        sp_res = self.pia_sys_conn_check()
        if (sp_res == 'Connected'):
            return True
        else:
            i = 0
            while i < 5:
                subprocess.run('piactl connect')
                time.sleep(1)
                sp_res = self.pia_sys_conn_check()
                if(sp_res == 'Connected'):
                    return True
        return False

    def filter_torrent_by_hash(self, t_hash: str, torrents=None):
        tor_check = torrents if torrents != None else self.get_current_torrents()

        for tor in tor_check:
            if tor.hash_string == t_hash:
                return tor
        return None

    def download_torrent(self, torrent_url) -> str:

        full_path, response = self.add_torrent(torrent_url)
        if(not response.result == 'success'):
            raise Exception('Torrent add failed')

        t_hash: str = ''
        if(response.arguments.torrent_added != None):
            t_hash = response.arguments.torrent_added.hash_string
        elif(response.arguments.torrent_duplicate != None):
            t_hash = response.arguments.torrent_duplicate.hash_string

        downloaded = False

        self.vvn1_mongo_client.update_downloading_status(self.guild_id,self.movie,True)
        start_time = time.time()
        while(not downloaded):
            torrent = None
            torrent = self.filter_torrent_by_hash(t_hash)
            if not torrent:
                raise Exception('No torrent found')
            cur_time = int(time.time()-start_time)
            self.vvn1_mongo_client.update_percent(
                self.guild_id, self.vvn1_mongo_client.DOWNLOADING, self.movie,round(torrent.percent_done*100, 1), cur_time)
            time.sleep(1)

            if(torrent.percent_done == 1):
                downloaded = True
                return full_path
                # return torrent.name

            if(cur_time > 200 and torrent.percent_done == 0):
                self.vvn1_mongo_client.download_error(
                    self.guild_id, self.movie)
                raise 'Error downloading'

    def add_torrent(self, torrent_url):
        # encapsulating whatever is torrented one extra level. going to fix before leaving this dl circuit
        movie_name_no_space = self.movie['movieName'].strip()
        full_dl_dir = os.path.join(download_dir, movie_name_no_space)

        try:

            download_args: TorrentAddArguments = {
                "filename": torrent_url,
                "download_dir": full_dl_dir
            }

            response: Response[TorrentAdd] = self.torrent_client.torrent.add(
                download_args)
            return full_dl_dir, response

        except Exception as exp:
            raise Exception(
                'Error adding torrent. Check the that was provided url')

    def get_current_torrents(self) -> list:
        response = self.torrent_client.torrent.accessor(all_fields=True)

        torrents = response.arguments.torrents
        return torrents

    def remove_torrents(self):
        torrents = self.get_current_torrents()
        torrents_len = len(torrents)
        if(torrents_len < 1):
            pass
        else:
            [self.torrent_client.torrent.remove(
                torrent.id, False) for torrent in torrents]

    def zip_movie(self,movie_path):
        zip_name = self.movie['zipName']
        zip_password = self.movie['zipPassword']

        files = [f.path for f in os.scandir(movie_path) if f.is_file() and f.path.endswith('.zip')]
        if len(files)>0:
            #if we find the zip then we make sure it has the name we want
            hd_zip_name = files[0]           
            new_name = os.path.join(os.path.dirname(hd_zip_name)  , zip_name)
            os.rename(hd_zip_name,new_name)
            hd_zip_name = new_name
        

        else:

            hd_zip_name = os.path.join(movie_path,zip_name)
            zip_command = ['zip','-j','-r']
            if zip_password!='':
                zip_command.append('--password')
                zip_command.append(zip_password)
            
            zip_command.append(zip_name)
            zip_command.append('.')

            subprocess.run(zip_command,stdout=subprocess.DEVNULL,cwd=movie_path)
        
        return hd_zip_name

'''
TODO:   
    prompt for a movie to delete if no room to add 

'''
