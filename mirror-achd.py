#!/usr/bin/python

import glob
import os
import os.path
import stat
import tempfile
import time
import urllib2

source_url = "https://alleghenycounty.us/hd/DailySummary.PDF"


os.chdir(os.path.dirname(__file__))
dest_dir = "mirror"
tmp_dir = "tmp"

def now():
    return time.strftime('%Y-%m-%d-%H:%M:%S%z')

def find_most_recent_path(source):
    (base, ext) = os.path.splitext(os.path.basename(source_url))
    mirrored_files = sorted(glob.glob(dest_dir + "/" + base + "-????-??-??-??:??:??*" + ext))
    if len(mirrored_files) == 0:
        return None
    return mirrored_files[-1]

def mirror_now(source, dest_dir, tmp_dir):
    try:
        os.mkdir(dest_dir)
    except OSError:
        pass
    try:
        os.mkdir(tmp_dir)
    except OSError:
        pass

    (base, ext) = os.path.splitext(os.path.basename(source_url))
    log_path = dest_dir + "/" + base + "-log.txt"
    log = open(log_path, "a")
    
    log.write("%s: Fetching %s\n" % (now(), source))
    log.flush()

    start_time = time.time()
    try:
        response = urllib2.urlopen(source, timeout=600).read()
    except urllib2.HTTPError as e:
        log.write("%s: Couldn't read %s because %s\n" % (now(), source, e))
        log.flush()
        return
    log.write("%s: Read %d bytes from %s in %.1f seconds\n" % (now(), len(response), source, time.time() - start_time))
    log.flush()

    most_recent_path = find_most_recent_path(source)
    if most_recent_path and open(most_recent_path).read() == response:
        log.write("%s: Not recording %d bytes read from %s because identical to previous file %s\n" % (now(), len(response), source, most_recent_path))
        log.flush()
    else:
        dest = "%s/%s-%s%s" % (dest_dir, base, now(), ext)
        out = tempfile.NamedTemporaryFile(dir=tmp_dir, delete=False)
        out.write(response)
        out.close()
        os.chmod(out.name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.rename(out.name, dest)
        log.write("%s: Stored %d bytes read from %s at path %s\n" % (now(), len(response), source, dest))
        log.flush()

if __name__ == "__main__":
    os.umask(022)
    mirror_now(source_url, dest_dir, tmp_dir)
