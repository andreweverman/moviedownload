# moviedownload

### Used in conjunction with [vvn1-ts](https://github.com/andreweverman/vvn1-ts) to download magnet files and zip them up to Mega.nz for easy movie sharing.
#### Flow is:
* Checks for a movie download request in mongo
* Check that VPN is on
* Download the torrent 
* Zip the file according to user specification
* Upload to mega
* Set link in mongo

#### If a user says it is time to delete a movie, this will also remove from mega.
