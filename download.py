import json
import uuid
import shutil
from clutch import Client
from requests import Response
from clutch.schema.user.method.torrent.add import TorrentAddArguments
from clutch.schema.user.response.torrent.add import TorrentAdd
import time
import subprocess
import os
from mongo_util import VVN1MongoClient
import pika

ip_addr = os.getenv("TRANSMISSION_IP")
transmission_username = os.getenv("TRANSMISSION_USERNAME")
transmission_password = os.getenv("TRANSMISSION_PASSWORD")
download_dir = os.getenv("DOWNLOAD_DIR")
broker_url = os.getenv("BROKER_URL")




if not (ip_addr and download_dir):
    raise Exception(
        'Must set all environment variables: MEGA_EMAIL,MEGA_PASSWORD,TRANSMISSION_IP,UPLOAD_DIR,DOWNLOAD_DIR')


class DownloadClient():
    def __init__(self, guild_id):

        self.torrent_client = Client(
            address=ip_addr,
            username=transmission_username,
            password=transmission_password)
        self.vvn1_mongo_client = VVN1MongoClient()
        self.guild_id = guild_id
        self.download_dir = download_dir
        params =  pika.URLParameters(broker_url)
        params.socket_timeout = 5
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.queue_declare('statusUpdate',durable=True)

    def download(self, request):
        
        request['id'] = str(uuid.uuid4())
        self.request = request
        torrent_url = self.request['torrentLink']

        pia_conn = self.check_pia()
        if(not pia_conn):
            return 'Not connected to VPN. Quitting...'
        movie_dir_name,torrent = self.download_torrent(torrent_url)
        final_dir = self.fix_dir(movie_dir_name)
        self.remove_torrent(torrent)
        self.turn_off_pia_if_no_more_torrents()

        return final_dir


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
                popen = subprocess.Popen(
                ['piactl', 'connect'], stdout=subprocess.PIPE)
                time.sleep(1)
                sp_res = self.pia_sys_conn_check()
                if(sp_res == 'Connected'):
                    return True
        return False

    def turn_off_pia(self):
        sp_res = self.pia_sys_conn_check()
        if (sp_res == 'Connected'):
            i = 0
            while i < 5:
                popen = subprocess.Popen(
                ['piactl', 'disconnect'], stdout=subprocess.PIPE)
                time.sleep(1)
                sp_res = self.pia_sys_conn_check()
                if(sp_res != 'Connected'):
                    return True
        else:
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

        while(not downloaded):
            torrent = None
            torrent = self.filter_torrent_by_hash(t_hash)
            if not torrent:
                raise Exception('No torrent found')

            percent_done = round(torrent.percent_done*100, 1)
            
            self.send_status_update(percent_done,torrent.eta)
            time.sleep(3)

            if(torrent.percent_done == 1):
                downloaded = True
                self.send_status_update(100,torrent.eta)
                return full_path,torrent
                # return torrent.name



    def add_torrent(self, torrent_url):
        # encapsulating whatever is torrented one extra level. going to fix before leaving this dl circuit
        movie_name_no_space = self.request['movieName'].strip()
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
                f'Error adding torrent. Check that it was provided url\n{exp}')

    def get_current_torrents(self) -> list:
        response = self.torrent_client.torrent.accessor(all_fields=True)

        torrents = response.arguments.torrents
        return torrents

    def turn_off_pia_if_no_more_torrents(self,):
        if len(self.get_current_torrents()) ==0:
            self.turn_off_pia()


    def remove_torrent(self,torr=None):
        torrents = self.get_current_torrents()
        torrents_len = len(torrents)
        if torr:
            # means we are deleting a specific one
            [self.torrent_client.torrent.remove(
                    torrent.id, False) for torrent in torrents if torr.id == torrent.id]


        else:   
            if(torrents_len < 1):
                pass
            else:
                [self.torrent_client.torrent.remove(
                    torrent.id, False) for torrent in torrents]




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
                    new_outer_name = os.path.join(self.download_dir,os.path.basename(check_dir))
                    file_list = [f.path for f in os.scandir(check_dir)]
                    for f in file_list:
                        shutil.move(f, outer_dir)
                break
                
        if first_sub_dir != '':
            shutil.rmtree(first_sub_dir)
        
        # TODO: can add a prop to the download thing for the dir name in this case

        if new_outer_name != '' and not os.path.exists(new_outer_name) and os.path.exists(outer_dir):
            os.rename(outer_dir,new_outer_name)
            self.vvn1_mongo_client.add_path_to_drq(self.guild_id,self.movie,new_outer_name)

        return new_outer_name if new_outer_name != '' else outer_dir

    def send_status_update(self,percent_done,time_remaining:str):
        body = self.request.copy()
        body['percentDone'] = percent_done
        body['timeRemaining'] = time_remaining
        self.channel.basic_publish(exchange='',routing_key='statusUpdate',body=json.dumps(body))