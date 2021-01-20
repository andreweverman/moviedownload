import logging
from moviedownload import DownloadClient
from flask import Flask, escape, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash,check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

users = {
    'vvn1':generate_password_hash('garbage whistle'),
    'old_computer':generate_password_hash('vermin pistol')
}

@auth.verify_password
def verify_password(username,password):
    if username in users and check_password_hash(users.get(username),password):
        return username

download_client = DownloadClient()
@app.route('/download',methods=['POST'])
@auth.login_required
def downloadmovie():
    
    result = {'downloaded':False,'errorReason':''}
    try:
        
        request_params = request.get_json()
        movie_name = request_params.get('movie_name')
        torrent_url = request_params.get('torrent_url')
        zip_name = request_params.get('zip_name')
        zip_password = request_params.get('zip_password')
        if not movie_name or not torrent_url or not zip_name:
            result['errorReason']  = 'missing arguments'
        else:
            result = download_client.download_and_upload(movie_name,torrent_url,zip_name,zip_password)
    
    except Exception as excp:
        result['errorReason'] = excp.args[0]
    finally:
        return result

app.run()