from mega import Mega
from shutil import copyfile
from clutch import Client
from requests import Response
import json
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.add import TorrentAdd
import threading
import time
import logging
import subprocess
import os
from dotenv import load_dotenv
load_dotenv()

username = os.getenv("MEGA_EMAIL")
password = os.getenv("MEGA_PASSWORD")
ip_addr = os.getenv("TRANSMISSION_IP")
movie_dir = os.getenv("MOVIE_DIR")

if not (username and password and ip_addr and movie_dir):
    raise Exception('Must set all environment variables: MEGA_EMAIL,MEGA_PASSWORD,TRANSMISSION_IP,MOVIE_DIR')
class DownloadClient:
    def __init__(self):
        self.mega_client = Mega()
        self.mega = self.mega_client.login(
            username, password)
        self.torrent_client = Client(
            address=ip_addr)
        self.parent_node_id=''

    def get_mega_files(self) -> list:
        files = self.mega.get_files()
        folder_file = None
        for file_key in files:
            file = files[file_key]
            if(file['a']['n'] == 'vvn1'):
                folder_file = file
                break

        if(not folder_file):
            return []
        file_id = folder_file['h']
        self.parent_node_id=file_id
        current_movies = []
        for file_key in files:
            file = files[file_key]
            if file['p'] == file_id:
                current_movies.append(file)

        return current_movies

    def new_mega_file(self,name:str):
        done = False
        while not done:

            files = self.get_mega_files()
            for file in files:
                if file['a']['n']==name:
                    return file
            
            time.sleep(10)

        
        

    def upload_movie(self,container_dir, movie_dir):
        # need to zip files and then upload to mega
        directory = os.path.join(container_dir, movie_dir)

        zip_name = input("Enter zip name: ") + '.zip'
        zip_p = os.path.join(directory,zip_name)

        subprocess.run(['zip','-r','--password','hotdog',zip_p,directory],stdout=subprocess.DEVNULL)
     
        
        copyfile(zip_p,movie_dir+zip_name)

        return self.new_mega_file(zip_name)

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

    def download_and_upload(self,movie_name,torrent_url, zip_name,zip_password):
        pia_conn =self.check_pia()
        if(not pia_conn):
            return 'Not connected to VPN. Quitting...'
        file_ps = self.download_torrent(torrent_url)

        self.upload_movie(file_ps[0],file_ps[1])

        pass

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
        while(not downloaded):
            torrent=None
            torrent = self.filter_torrent_by_hash(t_hash)
            if not torrent:
                raise Exception('No torrent found')
            print('\r%d percent, %d mbs left' % (torrent.percent_done*100, torrent.left_until_done/1000000),end="")
            time.sleep(1)

            if(torrent.percent_done==1):
                downloaded=True
                print('Download Complete')
                return [torrent.download_dir,torrent.name]


    def add_torrent(self,torrent_url):
        try:
    
            download_args: TorrentAddArguments = {
                "filename": torrent_url,
                "download_dir": '/data/Movies'
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
            print('No torrents to remove')
        else:
            [self.torrent_client.torrent.remove(
                torrent.id, False) for torrent in torrents]
            print("%d torrent(s) removed" % torrents_len)


# client = DownloadClient()
# client.download_and_upload()
# client.download_torrent()
# client.remove_torrents()
# client.get_mega_files()

'''
TODO:   
    prompt for a movie to delete if no room to add 

'''
