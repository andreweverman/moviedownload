import json
import os
import sys
from PyDictionary import PyDictionary
import PTN
import pronouncing
import nltk
import subprocess
import re
import shutil


class Base():
    username = os.getenv("MEGA_EMAIL")
    password = os.getenv("MEGA_PASSWORD")
    ip_addr = os.getenv("TRANSMISSION_IP")
    download_dir = os.getenv("DOWNLOAD_DIR")
    upload_dir = os.getenv("UPLOAD_DIR")
    def __init__(self):
        pass

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

    def zip_movie(self, movie_path, desired_zip_name, zip_password,movie_name=''):
        zip_name = desired_zip_name
        if not os.path.isdir(movie_path):
            raise 'Error creating new zip: Could not find directory to zip'

        base_name = os.path.basename(movie_path)
        if movie_name =='':
            movie_name = PTN.parse(base_name)['title']
        if zip_name == '':
            zip_name = self.new_name(movie_name)
        
        spec_file = self.get_spec_file(movie_path)

        if spec_file:
            return {'path':spec_file['zipPath'],'password':spec_file['zipPassword']}

        found_zip_files = [f.path for f in os.scandir(
            movie_path) if f.is_file() and f.path.endswith('.zip')]
        if len(found_zip_files) > 0:
            # if we find the zip then we make sure it has the name we want
            hd_zip_name = found_zip_files[0]
            new_name = os.path.join(os.path.dirname(hd_zip_name), zip_name)
            os.rename(hd_zip_name, new_name)
            hd_zip_name = new_name

        else:

            hd_zip_name = os.path.join(movie_path, zip_name)
            zip_command = ['zip', '-j', '-r']
            if zip_password != '':
                zip_command.append('--password')
                zip_command.append(zip_password)

            zip_command.append(zip_name)
            zip_command.append('.')

            subprocess.run(
                zip_command, stdout=subprocess.DEVNULL, cwd=movie_path)


            self.create_spec_file(movie_path,movie_name,hd_zip_name,zip_password)
            

        return {'path':hd_zip_name,'password':zip_password}

    def new_name(self, name):
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

        bad_boys = ['DT']

        tokenized = nltk.word_tokenize(name)
        words = nltk.pos_tag(tokenized)

        dic = PyDictionary()

        all_words = []
        for tupp in words:
            word = tupp[0]
            ant = dic.antonym(word)
            added = False

            if tupp[1] not in bad_boys:
                if ant:
                    all_words.append(ant[0].title().replace(' ', ''))
                    added = True

                else:
                    syn = dic.synonym(word)
                    if syn:
                        all_words.append(syn[0].title().replace(' ', ''))
                        added = True
                    else:
                        rhymes = pronouncing.rhymes(word)
                        if rhymes and len(rhymes) > 0:
                            all_words.append(
                                rhymes[0].title().replace(' ', ''))
                            added = True
            if not added:
                all_words.append(word.title())

        sys.stdout = old_stdout
        return re.sub(r'\W+', '', ''.join(all_words)) + '.zip'

    def create_spec_file(self, movie_dir, movie_name, zip_path, zip_password):
        if not os.path.isdir(movie_dir):
            raise 'Error: Invalid movie directory'
        
        obj = {'movieName': movie_name,'zipPath':zip_path,'zipPassword':zip_password}
        with open(os.path.join(movie_dir, 'spec.json'),'w') as f:
            json.dump(obj,f,indent=4)
        pass


    def get_spec_file(self, movie_dir):
        if not os.path.isdir(movie_dir):
            raise 'Error: Invalid movie directory'
        
        found_specs = [f.path for f in os.scandir(
            movie_dir) if f.is_file() and f.path.endswith('spec.json')]
        if len(found_specs)<1:
            return None
        spec_file_path = found_specs[0]

        with open(spec_file_path, 'r') as f:
            return json.load(f)
            