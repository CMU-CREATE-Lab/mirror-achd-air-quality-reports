#!/usr/bin/env python

# Execute this cell to define the functions for calling the Fluxtream upload API for the 
# credentials entered below
import json, subprocess

# By default, the upload function will send data to the main server at fluxtream.org.  
# If you want to have this use a different fluxtream server, change it here
# and make sure the username and password entered below are valid on that server.
global fluxtream_server
fluxtream_server = "fluxtream.org"

def setup_fluxtream_credentials():
    # Call the Fluxtream guest API, documented at 
    #   https://fluxtream.atlassian.net/wiki/display/FLX/BodyTrack+server+APIs#BodyTrackserverAPIs-GettheIDfortheguest

    # Make sure it works and harvest the Guest ID for future use
    global fluxtream_server, fluxtream_username, fluxtream_password, fluxtream_guest_id

    # Make sure we have fluxtream credentials set properly
    if not('fluxtream_server' in globals() and 
           'fluxtream_username' in globals() and
           'fluxtream_password' in globals()):
        raise Exception("Need to enter Fluxtream credentials before uploading data.  See above.")

    cmd = ['curl', '-v']
    cmd += ['-u', '%s:%s' % (fluxtream_username, fluxtream_password)]
    cmd += ['https://%s/api/guest' % fluxtream_server]

    result_str = subprocess.check_output(cmd)
    #print '  Result=%s' % (result_str)

    try:
        response = json.loads(result_str)

        if 'id' in response:
            fluxtream_guest_id = int(response['id'])
        else:
            raise Exception('Received unexpected response %s while trying to check credentials for %s on %s' % (response, 
                                                                                                            fluxtream_username, 
                                                                                                            fluxtream_server))

        print 'Verified credentials for user %s on %s work. Guest ID=%d' % (fluxtream_username, fluxtream_server, fluxtream_guest_id)
    except:
        print "Attempt to check credentials of user %s failed" % (fluxtream_username)
        print "Server returned response of: %s" % (result_str)
        print "Check login to https://%s works and re-enter your Fluxtream credentials above" % (fluxtream_server)
        raise
    
def fluxtream_upload(dev_nickname, channel_names, data):
    global fluxtream_server, fluxtream_username, fluxtream_password
    
    # Make sure we have some data to send
    if data == None or len(data)<1:
        print 'Nothing to upload to %s %s' % (dev_nickname, channel_names)        
        return

    # Make sure we have fluxtream credentials set properly
    if not('fluxtream_server' in globals() and 
           'fluxtream_username' in globals() and
           'fluxtream_password' in globals()):
        raise Exception("Need to enter Fluxtream credentials before uploading data.  See above.")

    # Send to BodyTrack upload API, documented at 
    #   https://fluxtream.atlassian.net/wiki/display/FLX/BodyTrack+server+APIs#BodyTrackserverAPIs-Storingdata
    cmd = ['curl', '-v']
    cmd += ['-u', '%s:%s' % (fluxtream_username, fluxtream_password)]
    cmd += ['-d', 'dev_nickname=%s' % dev_nickname]
    cmd += ['-d', 'channel_names=%s' % json.dumps(channel_names)]
    cmd += ['-d', 'data=%s' % json.dumps(data)]
    cmd += ['https://%s/api/bodytrack/upload' % fluxtream_server]

    result_str = subprocess.check_output(cmd)
    #print '  Result=%s' % (result_str)

    try:
        response = json.loads(result_str)
        if response['result'] != 'OK':
            print 'Tried to upload channels >%s<' % json.dumps(channel_names)
            print 'Tried to upload data >%s<' % json.dumps(data)
            raise Exception('Received non-OK response %s while trying to upload to %s' % (response, dev_nickname))
        
        print 'Upload to %s %s (%d rows, %d to %d) succeeded' % (dev_nickname, channel_names, len(data), data[0][0], data[-1][0])
    except:
        print "Attempt to upload to %s as user %s failed. Check that your credentials are ok" % (fluxtream_server, 
                                                                                                 fluxtream_username)
        print "Server returned response: %s" % (result_str)
        raise

###############################

global fluxtream_username, fluxtream_password
fluxtream_username = "achd"
fluxtream_password = "achdmirror"
setup_fluxtream_credentials()

###############################

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
    def __sub__(self, rhs):
        return Point(self.x - rhs.x, self.y - rhs.y)
        
    def __repr__(self):
        return 'Point2(%g, %g)' % (self.x, self.y)

class Bbox:
    def __init__(self, str):
        (self.left, self.top, self.right, self.bottom) = [float(e) for e in str.split(',')]
        
    def __repr__(self):
        return 'Bbox(%g, %g, %g, %g)' % (self.top, self.left, self.bottom, self.right)
    
    def center(self):
        return Point(0.5 * (self.left + self.right), 0.5 * (self.top + self.bottom))
    
    def width(self):
        return self.right - self.left
    
    def height(self):
        return self.bottom - self.top
    

#############################

import datetime
from dateutil import tz

pgh_tz = tz.gettz("America/New_York")

log_lines = []

def reset_log():
    global log_lines
    log_lines = []
    
def log(msg):
    global log_lines
    print msg
    log_lines.append(datetime.datetime.now(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S%z') + ' ' + msg)
    
def get_log():
    return '\n'.join(log_lines)
    
def epoch_time(dt):
    epoch = datetime.datetime(1970, 1, 1, tzinfo=tz.tzutc())
    return (dt - epoch).total_seconds()    

def sanitize_name(name):
    return re.sub('\W', '_', name.encode('utf8'))

def process_achd_site(achd_site, base_datetime, achd_table):
    # Replace non-alphanum with underscores in achd_site
    devname = "ACHD_%s" % (re.sub('\W', '_',achd_site))
    channel_names = []

    # Process the header into channel names
    for i in range (1, len(achd_table[0])):
        channel_names.append(sanitize_name('%s_%s' % (achd_table[0][i], achd_table[1][i])))
    
    log("Found devname=%s, channels=%s, starting %s" % (devname, channel_names, base_datetime))
    
    rowcount = 0;
    data_cols = [[] for x in range(0, len(channel_names))]
    
    for i in range (2, len(achd_table)):
        row = achd_table[i]
        
        # Add base_datetime to the first column of the row, which is the local time within that date
        local_row_hour =  datetime.datetime.strptime(row[0], '%H:%M')
        local_row_datetime = base_datetime.replace(hour= local_row_hour.hour).replace(tzinfo=pgh_tz)
        unix_ts = epoch_time(local_row_datetime)
        
        
        for j in range (1, len(row)):
            try:
                data_row = [unix_ts]
                val_str = row[j].encode('utf8')
                if " " in val_str:
                    # condensation
                    val_elts = val_str.split(' ')
                    val_str = val_elts[0]
                    annotation = val_elts[1]
                    #print "Ignoring annotation %s on %s, using %s [%d][%d]" % (annotation, row[j], val_str, i, j)
            
                data_row.append(float(val_str))
                data_cols[j-1].append(data_row)
            except:
                pass
            
    for i in range (0, len(channel_names)):
        fluxtream_upload(devname, [ channel_names[i] ], data_cols[i])
        log("Uploaded %d samples to devname=%s, channels=%s, starting %s" % 
            (len(data_cols[i]), devname, channel_names[i], base_datetime))

#####################

import datetime, math, os, re, xml.dom.minidom

def parse_textline(textline):
    bbox = Bbox(textline.getAttribute('bbox'))
    text = ''.join([elt.firstChild.nodeValue for elt in textline.getElementsByTagName('text')])
    return {'bbox':bbox, 'text': text}

def process_page(page):
    textlines = [parse_textline(textline) for textline in page.getElementsByTagName('textline')]

    # Find site
    site = None

    for (i, textline) in enumerate(textlines):
        if textline['text'].strip() == 'Site:':
            site_textline = textlines[i + 1]
            deltapos = textline['bbox'].center() - site_textline['bbox'].center()
        
            if abs(deltapos.y) > 3:
                raise Exception('Confused about y location while trying to locate site')
        
            if deltapos.x > 0 or deltapos.x < -100:
                raise Exception('Confused about x location while trying to locate site')
        
            if site:
                raise Exception('Found more than one site?')
        
            site = site_textline['text'].strip()

    if not site:
        raise Exception("Couldn't parse site")

    log('Site: %s' % site)

    # Find date
    date = None
    for textline in textlines:
        if re.match(r'\d+/\d+/\d+$', textline['text'].strip()):
            if date:
                raise Exception('Found more than one date?')
            date = datetime.datetime.strptime(textline['text'].strip(), '%m/%d/%Y')

    if not date:
        raise Exception("Couldn't find date")

    log('Date: %s' % date)

    toprow = None
    bottomrow = None
    columns = []

    # Find row locations
    for textline in textlines:
        if textline['text'].strip() == '00:00':
            if toprow:
                raise Exception('Found more than one toprow?')
            toprow = textline['bbox'].center().y
            columns.append(textline['bbox'].center().x)
        if textline['text'].strip() == '23:00':
            if bottomrow:
                raise Exception('Found more than one bottomrow?')
            bottomrow = textline['bbox'].center().y

    if not toprow or not bottomrow:
        raise Exception("Couldn't find row landmarks")

    def compute_row(textline):
        fraction = (toprow - textline['bbox'].center().y) / float(toprow - bottomrow)
        row = round((fraction * 23) + 2)
        if (row < 0 or row > 25):
            return None
        return int(row)

    # Find columns
    for textline in textlines:
        if 0 == compute_row(textline):
            columns.append(textline['bbox'].center().x)

    columns = sorted(columns)

    def compute_col(textline):
        x = textline['bbox'].center().x
        best = 0
        for i in range(0, len(columns)):
            if abs(x - columns[i]) < abs(x - columns[best]):
                best = i
        return best

    table = [[None] * len(columns) for row in range(0, 26)]

    # Build table
    # Find columns
    for textline in textlines:
        row = compute_row(textline)
        if row != None:
            col = compute_col(textline)
            table[row][col] = textline['text'].strip()

    process_achd_site(site, date, table)
    
def process_doc(doc):
    for (pageno, page) in enumerate(doc.getElementsByTagName('page')):
        log('-------------------------------------------------------------------------------')
        log('Processing page %d' % pageno)
        process_page(page)
        log('-------------------------------------------------------------------------------')


def process_pdf(pdf_path):
    done_dir = 'upload-to-fluxtream'
    try:
        os.mkdir(done_dir)
    except OSError:
        pass
    done_path = done_dir + '/' + os.path.basename(os.path.splitext(pdf_path)[0]) + '.successful-upload'
    if os.path.exists(done_path):
        log('%s already uploaded, skipping' % pdf_path)
        return
    reset_log()
    log('Parsing and uploading %s' % pdf_path)
    log('Converting %s to xml' % pdf_path)
    xml_content = subprocess.check_output(['pdf2txt.py', '-t', 'xml', pdf_path])
    print 'pdf length %d converted to xml length %d' % (os.stat(pdf_path).st_size, len(xml_content))

    doc = xml.dom.minidom.parseString(xml_content)
    process_doc(doc)
    open(done_path + '.tmp', 'w').write(get_log())
    os.rename(done_path + '.tmp', done_path)    

########################

import glob

for pdf in sorted(glob.glob('mirror/*.PDF')):
    process_pdf(pdf)

