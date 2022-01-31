import os
from traceback import print_tb
import requests
import unicodedata
import string
from tqdm import tqdm

token = os.environ['NOTION_TOKEN']

class DownloadException(BaseException):
    pass

class GetDatabaseException(BaseException):
    pass

valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
char_limit = 255

def clean_filename(filename, whitelist=valid_filename_chars):
    
    
    # keep only valid ascii chars
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    
    # keep only whitelisted chars
    cleaned_filename = ''.join(c for c in cleaned_filename if c in whitelist)
    if len(cleaned_filename)>char_limit:
        print("Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(char_limit))
    return cleaned_filename[:char_limit] 

def download_pdf(path="", filename="paper.pdf", url="https://arxiv.org/pdf/1511.06434.pdf"):
    filename = clean_filename(filename)

    r = requests.get(url, stream=True)
    total_size_in_bytes= int(r.headers.get('content-length', 0))
    block_size = 1024 #1 Kibibyte
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    progress_bar.set_description(f"Downloading {filename} from {url}")
    with open(os.path.join(path, filename), 'wb') as file:
        for data in r.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)

    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        raise DownloadException(f"Can't download {url}")

def update_database(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization":f"Bearer {token}",
        "Notion-Version": "2021-08-16",
        "Content-Type": "application/json"
    }
    data = """
    {
        "properties": {
            "Downloaded": { "checkbox": true }
        }
    }
    """

    r = requests.patch(url, headers=headers, data=data)

    if r.status_code == 200:
        print("Database updated.")

def get_databases(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization":f"Bearer {token}",
        "Notion-Version": "2021-08-16",
        "Content-Type": "application/json"
    }
    data = """
    {
        "filter": {
            "property": "Downloaded",
            "checkbox": {
                "equals": false
            }
        }
    }
    """
    r = requests.post(url, headers=headers, data=data)
    if r.status_code != 200:
        raise GetDatabaseException(f"Can't open database")

    r = r.json()
    
    for item in r['results']:
        if item['properties']['Downloaded']['checkbox'] == True:
            continue
        
        title = item['properties']['Title']['title'][0]['text']['content']
        url = item['properties']['URL']['url']
        page_id = item['id']
        if url == None:
            print(f"{title} doesn't provide paper download link.")
            continue
        
        if url.find('arxiv') != -1:
            idx = url.rfind("/")
            id = ""
            cnt = 0
            for i in range(idx, len(url)):
                if '0' <= url[i] <= '9':
                    id += url[i]
                elif url[i] == '.':
                    if cnt == 0:
                        id += url[i]
                        cnt += 1
                    else:
                        break
            title = f"{id} {title}"
            url = f"https://arxiv.org/pdf/{id}.pdf"
        try:
            download_pdf(path="G:\\我的雲端硬碟\\Papers", filename=f"{title}.pdf", url=url)
            update_database(page_id)
        except DownloadException:
            continue

if __name__ == '__main__':
    database_id = "7de9310eb3fb4269a7370d2ed3d33152"
    get_databases(database_id)
