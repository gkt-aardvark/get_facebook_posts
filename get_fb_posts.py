from facebook_scraper import get_posts
import json
import pandas as pd
import sqlite3
import requests
import os
import sys
import argparse

parser = argparse.ArgumentParser(description='Pull data for a single public Facebook user account.')

parser.add_argument('-u', '--user', type=str, help='Specify single Facebook user account name.', dest='user', required=True)
parser.add_argument('-p', '--pages', type=int, help='Number of pages (2 on first page, 4 on subsequent). Default is 10.', default=10, dest='num_pages')
parser.add_argument('-m', '--get_media', help='Download media (video/images) or not. Default is False.', default=False, action='store_true')
parser.add_argument('-d', '--destination', type=str, help='Output folder name. Defaults to username.', dest='output_dir')
args = parser.parse_args()

#assign args to variables of their own
user = args.user
num_pages = args.num_pages
output_dir = args.output_dir

#if output_dir is not specified, user the user name
if output_dir is None:
    output_dir = user
get_media = args.get_media

if not os.path.isdir(output_dir):
    os.mkdir(output_dir)
    
#create paths based on username and define csv/sqlite/image/videos output stuff

db_path = os.path.join(output_dir, f'fb_posts_{user}.db')
csv_path = os.path.join(output_dir, f'fb_posts_{user}.csv')
vid_path = os.path.join(output_dir, 'video')
img_path = os.path.join(output_dir, 'images')

#calculate number of posts that should be based on pages
#two for first page, four for each subsequent page
num_posts = (num_pages * 4) - 2

#login with your burner account to get more stuff
#this is NOT CURRENTLY WORKING with this library
fb_user = 'your_sock_or_burner_account'
fb_pw = 'your_fb_password'
creds = (fb_user, fb_pw)

def get_all_posts(user, num_pages):
    '''
    take username(account) and number of pages
    and get posts and return them as a list
    '''
    
    try:
        posts = [post for post in get_posts(account=user, 
                                            pages=num_pages, 
                                            extra_info=True,
                                            )
                ]
        return posts
        
    except requests.exceptions.HTTPError:
        print ('[-] Sorry, user has no public posts.')
        return False

    
def to_json(data):
    '''
    images list is a list and we must jsonify it for insertion into sqlite3
    '''
    
    return json.dumps(data)
    
if __name__ == '__main__':
    
    #get posts
    print (f'[!] Attempting to get {num_posts} posts from account {user}...')
    posts = get_all_posts(user, num_pages)
    
    if posts:
        #put data into a pandas dataframe, jsonify images list and reactions
        df = pd.DataFrame.from_records(posts)
        df['images'] = df.images.apply(to_json)
        
        #reactions are a dictionary, but are only there on certain posts
        try:
            df['reactions'] = df.reactions.apply(to_json)
        except AttributeError:
            pass
        
        #spew out as a sqlite db and csv
        print (f'[!] Creating csv file for posts from {user}')
        df.to_csv(csv_path, index=False, header=True)
        
        print (f'[!] Creating database for posts from {user}')
        conn = sqlite3.connect(db_path)
        df.to_sql('fb_posts', conn, index=False, if_exists='replace')
        conn.close()
        
        print (f'[+] Data saved in the {db_path} folder.')
        
        #removing the dataframe variable in case memory is an issue... atypical
        del df
        
        #get all image and video links
        if get_media:
            print ('[!] Attempting to retrieve all videos and images from retrieved posts.')
            
            #create video and image dirs if they don't exist
            if not os.path.isdir(img_path):
                os.makedirs(img_path)
            if not os.path.isdir(vid_path):
                os.makedirs(vid_path)
            for post in posts:
                images = post['images']
                video = post['video']
                
                if images is not None:
                    for i, image in enumerate(images):
                        filename = f'{user}_{post["post_id"]}_image{i}.jpg'
                        savepath = os.path.join(img_path, filename)
                        if not os.path.isfile(savepath): #check and see if we already have it
                            print (f'[+] Getting image {filename}...')
                            r = requests.get(image)
                            with open(savepath, 'wb') as f:
                                f.write(r.content)
                
                if video is not None:
                    filename = f'{user}_{post["post_id"]}.mp4'
                    savepath = os.path.join(vid_path, filename)
                    if not os.path.isfile(savepath): #check and see if we already have it
                        print (f'[+] Getting video {filename}...')
                        r = requests.get(video)
                        with open(savepath, 'wb') as f:
                            f.write(r.content)