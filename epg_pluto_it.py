import requests
import re
import sys
import uuid
import json
from datetime import datetime, timedelta, UTC
import time
import xml.etree.ElementTree as ET
import os


IT_REGION = os.environ.get("IT_REGION")

def date_converter(date_string):

    try:    
        date_obj=datetime.fromisoformat(date_string)
        if date_obj.tzinfo:
            date_formatted=date_obj.strftime('%Y%m%d%H%M%S %z')
        else:
            date_formatted=date_obj.strftime('%Y%m%d%H%M%S +0000')
        return date_formatted

    except:
        return ''


def append_json(epg_xml,epg_json, program_list):
    
    info_list = epg_json['data']

    for element in info_list:
        ch_id=element.get('channelId').strip()
        
        if not ch_id:
            continue

        for timeline in element.get('timelines', []):

            program_id=timeline.get('episode', {}).get('_id').strip()

            if not program_id:
                continue

            if program_id in program_list:
                continue
            
            prog_start= date_converter(timeline.get('start', '')).strip()
            if not prog_start:
                continue

            prog_end=date_converter(timeline.get('stop', '')).strip()
            if not prog_end:
                continue

            prog_xml = ET.SubElement(epg_xml, 'programme')
            
            prog_xml.attrib['start']=prog_start
            prog_xml.attrib['stop']=prog_end
            prog_xml.attrib['channel'] = ch_id
            
            prog_title=ET.SubElement(prog_xml, 'title')
            prog_title.text = timeline.get('title', 'No title').strip()

            prog_desc=ET.SubElement(prog_xml, 'desc')
            prog_desc.text=timeline.get('episode', {}).get('description', 'No description').strip()

            prog_icon=ET.SubElement(prog_xml, 'icon')
            
            prog_icon.attrib['src']=timeline.get('episode',{}).get('series',{}).get('tile',{}).get('path','').strip()

            program_list.add(program_id)

    return 1

            

def get_channel_list(token, channel_list):
    
    url='https://service-channels.clusters.pluto.tv/v2/guide/channels'
    
    url_parmams={
        'channelIds':'',
        'offset':'0',
        'limit':'1000',
        'sort':'number:asc',
        "region": "IT",
        "lang": "it",
        "timeZone": "Europe/Rome"
        }            

    headers={
        'Accept':'*/*',
        'Accept-encoding':'gzip, deflate, br, zstd',
        'Accept-language':'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Authorization':f'Bearer {token}',
        'X-Forwarded-For':IT_REGION
        }
    
    try:
        response=requests.get(url, params=url_parmams, headers=headers)
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f'Error during channels list request to {url}: {e}')
        return None    
        
    try:
        json_response=response.json()
        
    except json.JSONDecodeError:
        print(f'Imopssible to retrieve channels list using url {url}: no json to process')
        print(f'{response.text}')
        return None

    info_list = json_response.get('data')
    if not info_list:
        print(f'No channels info in json by {url}')
        return None

    for channel in info_list:
        #get channel id
        if  not channel.get('id').strip():
            #reset possible values assigned in the previous iteration
            channel_name =''
            channel_number=''
            channel_logo_color=''
            channel_logo_solid=''
            channel_logo = ''            
            continue
        channel_id=channel.get('id').strip()

        #get channel name
        channel_name=channel.get('name', 'Pluto TV').strip()

        #get channel number
 
        channel_number=channel.get('number','')
            
        #get channel logo
        channel_logo_list=channel.get('images')
        for logo in channel_logo_list:
            if logo.get('type')=='colorLogoPNG' and logo.get('url').strip():
                channel_logo_color = logo.get('url').strip()
            if logo.get('type')=='solidLogoPNG' and logo.get('url').strip():
                channel_logo_solid = logo.get('url').strip()
        if channel_logo_color:
            channel_logo = channel_logo_color
        elif channel_logo_solid:
            channel_logo = channel_logo_solid
        else:
            channel_logo = ''

        channel_list[channel_id] = {
            'name':channel_name,
            'lcn': channel_number,
            'logo':channel_logo
            }

    return 'OK'

 

def get_epg(start, token, input_channels):

    if not input_channels:
        print('No channels provided')
        return None
    
    start_date=start.replace(minute=0, second=0, microsecond=0)
    start_epg=start_date.strftime('%Y-%m-%dT%H:00:00.000Z')

    
    url='https://service-channels.clusters.pluto.tv/v2/guide/timelines'

    id_list=list(input_channels)  

    ch_ids=','.join(id_list)

    url_parmams={
        'start':f'{start_epg}',
        'channelIds':ch_ids,
        'duration':'240',
        "region": "IT",
        "lang": "it",
        "timeZone": "Europe/Rome"
        }
    
    headers={
        'Accept':'*/*',
        'Accept-encoding':'gzip, deflate, br, zstd',
        'Accept-language':'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-Forwarded-For':IT_REGION,
        'Authorization':f'Bearer {token}'
        }

    try:
        response=requests.get(url, params=url_parmams, headers=headers)
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f'Error during timeline request to {url}: {e}')
        return None
    
    try:
        json_response=response.json()
        
    except json.JSONDecodeError:
        print(f'Imopssible to retrieve timeline using url {url}: no json to process')
        print(f'{response.text}')
        return None

    return json_response    
    

def get_token(appversion, client_uiid):
    url='https://boot.pluto.tv/v4/start'
    params={
        'appName':'web',
        'appVersion':f'{appversion}',
        'clientID':f'{client_uiid}',
        'clientModelNumber':'1.2.0',
        "region": "IT",
        "lang": "it",
        "timeZone": "Europe/Rome"
        }
    headers={
        'X-Forwarded-For':IT_REGION
        }
    try:
        response=requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f'Error during token request to {url}: {e}')
        return None

    try:
        json_response=response.json()
        
    except json.JSONDecodeError:
        print(f'Imopssible to retrieve token using url {url}: no json to process')
        print(f'{response.text}')
        return None


    token=json_response.get('sessionToken')

    if not token:
        print(f'Imopssible to retrieve token using url {url}')
        return None

    return token



def get_appversion():
    url = "https://pluto.tv/"
    headers={
        'upgrade-insecure-requests': '1',
        'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'X-Forwarded-For':IT_REGION
        }

    try:    
        response = requests.get(url, headers = headers)
        response.raise_for_status()
        
        
    except requests.exceptions.RequestException as e:
        print (f'Error during request of {url}: {e}')
        return None
        
    html_file = response.text

    regex = r'name="appVersion".*?content="([^"]+)"'

    appversion_list = re.findall(regex, html_file)

    if not appversion_list:
        print(f'Response by {url} not valid: appversion missing!')
        return None
              
    if len(appversion_list) == 1:
        appversion = appversion_list[0]
        print(f'Appversion: {appversion}')
        return appversion

    else:
        print(f'Response by {url} not valid: multiple values of appversion!')
        return None



start_time = datetime.now(UTC)
start=start_time

####Get appversion and create session_uiid to use in the next request for token
appversion = get_appversion()

if not appversion:
    sys.exit()
    
client_uiid = str(uuid.uuid4())
print(f'client id:{client_uiid}')

#Get token to use in the requests for channels list and epg
session_token = get_token(appversion, client_uiid)

if not session_token:
    sys.exit()

print(f'session token: {session_token}')

#Get channels list
channel_list = {}

if get_channel_list(session_token, channel_list):
    print('Channels list obtained')

#####################da rimuovere #########################################à
with open('channel_list.txt', 'w') as f:
    
    for key, value in channel_list.items():
        ch_name=value['name']
        ch_number=str(value['lcn'])
        ch_logo=value['logo']
        f.write(f'id: {key}, name: {ch_name},  ch_n: {ch_number},   logo:{ch_logo}\n')
##############################################################################à

epg_xml = ET.Element('tv')
epg_xml.attrib['source-info-name'] = 'None'

for key, value in channel_list.items():
    
    ch_name=value['name']
    ch_number=str(value['lcn'])
    ch_logo=value['logo']
    
    channel_xml = ET.SubElement(epg_xml, 'channel')
    channel_xml.attrib['id']= key
    diplay_name=ET.SubElement(channel_xml, 'display-name')
    diplay_name.text=ch_name
    lcn=ET.SubElement(channel_xml, 'lcn')
    lcn.text=ch_number
    icon=ET.SubElement(channel_xml, 'icon')
    icon.attrib['src']=ch_logo


#Get json of epg
input_channels={}
id_list=list(channel_list)

program_list = set()

epg_time_frame = 48
increment = 0

full_epg_json ={'data':[]}

while increment <=  epg_time_frame:

    i=0

    while i<len(id_list):

        for current_id in id_list[i: i+30]:
            input_channels[current_id]=channel_list[current_id]
            
        epg_json=get_epg(start, session_token, input_channels)

        if not epg_json:
                continue

        full_epg_json['data'].extend(epg_json['data'])

        i=i+30
        input_channels.clear()
    increment = increment + 4 #240 minuti dell'url
    start = start + timedelta(hours=4)
    

epg_conversion = append_json(epg_xml,full_epg_json, program_list)

epg_ord = ET.Element(epg_xml.tag, epg_xml.attrib)

for element in epg_xml.findall('channel'):
    epg_ord.append(element)

program_element = epg_xml.findall('programme')
program_sorted = sorted(program_element, key = lambda p: p.attrib['channel'])

for element in program_sorted:
    epg_ord.append(element)

tree = ET.ElementTree(epg_ord)


ET.indent(tree, space='    ', level=0)

tree.write('epg_pluto_it.xml', encoding='utf-8', xml_declaration=True)

end_time = datetime.now(UTC)

process_time = end_time - start_time

print (f'Process terminated in {process_time}')
