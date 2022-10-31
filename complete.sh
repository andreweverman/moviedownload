#!/usr/bin/env bash
# Transmission script to move tiorrent files to post-processing


#################################################################################
# These are inherited from Transmission.                                        #
# Do not declare these. Just use as needed.                                     #
#                                                                               #
# TR_APP_VERSION                                                                #
# TR_TIME_LOCALTIME                                                             #
# TR_TORRENT_DIR                                                                #
# TR_TORRENT_HASH                                                               #
# TR_TORRENT_ID                                                                 #
# TR_TORRENT_NAME                                                               #
#                                                                               #
#################################################################################


#################################################################################
#                                    CONSTANTS                                  #
#                         configure directories and filetypes                   #
#################################################################################


# Use recursive hardlinks (cp -al) only if both Transmission's seed dir and 
# the final dir belong to the same filesystem.  Set to false to make a 
# duplicate copy. Note: true allows you to seed and copy without using up 
# twice the storage.
HARDLINKS=true

# The file for logging events from this script
LOGFILE="/hd2/log.log"



#################################################################################
#                                 SCRIPT CONTROL                                #
#                               edit with caution                               #
#################################################################################


function edate 
{
  echo "`date '+%Y-%m-%d %H:%M:%S'`    $1" >> "$LOGFILE"
 
}


edate "__________________________NEW TORRENT FINI _______________________"
edate "Version de transmission $TR_APP_VERSION"
edate "Time  $TR_TIME_LOCALTIME"
edate "Directory is $TR_TORRENT_DIR"
edate "Torrent Hash is $TR_TORRENT_HASH"
edate "Torrent ID is $TR_TORRENT_ID"
edate "Torrent name is $TR_TORRENT_NAME "
chown -R vvn1:debian-transmission $TR_TORRENT_DIR
