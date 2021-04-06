import subprocess
import sys
import time
import pexpect
import re

hd_zip_name = 'm\ b.flac'
upload_path = 'vvn1/'
upload_command  =  ' '.join(['mega-put',  hd_zip_name,upload_path])
# upload_command = './test.sh'
start_time = time.time()    
percent = 0

thread = pexpect.spawn(upload_command)
# cpl = thread.compile_pattern_list([pexpect.EOF, ':\s*\d+.\d+\s*%', 'Upload finished', '(.+)'])
cpl = thread.compile_pattern_list([pexpect.EOF, '\d+\.\d+\s*%'])
p_regex = re.compile(r'\d+\.\d+')

while True:
    i = thread.expect_list(cpl,timeout=None)
    if i==0:
        print("process exited")
        break
    elif i==1:
        output = thread.match.group(0).decode('utf-8')
        matched = re.findall(p_regex,output)                
        p_num = float(matched[0])        
        print("%.2f done" % p_num)

