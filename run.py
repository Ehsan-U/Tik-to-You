import hashlib
import random
import sqlite3
import subprocess
import time
from selenium.webdriver.common.by import By
from youtube_dl import YoutubeDL
import seleniumwire.undetected_chromedriver as uc
import os
from selenium.webdriver import ChromeOptions
import scrapy
from selenium.webdriver.common.action_chains import ActionChains

class TikYou():
    def __init__(self,username,limit):
        self.username = username.strip().replace(' ','')
        self.unique = list()
        self.url = f'https://www.tiktok.com/@{self.username}?lang=en'
        self.profile = f'C:\\Users\\{os.getlogin()}\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1'
        self.counter = 1
        self.max = 1
        self.min = 0
        self.limit = limit
        self.count = 1
        self.con = sqlite3.connect('youtube.db')
        self.cur = self.con.cursor()
        self.cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.username}(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                URL TEXT,
                META TEXT,
                HASH TEXT
                );
            """
        )
        self.cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.username}_UPLOADED (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                URL TEXT
                );
            """
        )


    def db(self,lookup=None,store=None,get=None):
        if lookup:
            url = lookup['url']
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            if lookup['upload']:
                self.cur.execute(f"SELECT * FROM {self.username}_UPLOADED WHERE URL = ?",(url_hash,))
            else:
                self.cur.execute(f"SELECT * FROM {self.username} WHERE HASH = ?", (url_hash,))
            exists = self.cur.fetchone()
            if exists:
                return False
            else:
                return True

        elif store:
            url = store['url']
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            if store['upload']:
                self.cur.execute(f"INSERT INTO {self.username}_UPLOADED(URL) VALUES (?)", (url_hash,))
            else:
                meta = store['meta']
                self.cur.execute(f"INSERT INTO {self.username}(URL,META,HASH) VALUES (?,?,?)", (url,meta,url_hash))
            print(" [+] Item added")
            self.con.commit()

        elif get:
            # if get['upload']:
            #     self.cur.execute(f"SELECT URL FROM {self.username}_UPLOADED")
            # else:
            self.cur.execute(f"SELECT URL,META FROM {self.username}")
            result = self.cur.fetchall()
            return result

    def get_driver(self):
        ch_opt = ChromeOptions()
        ch_opt.add_argument(f"user-data-dir':{self.profile}")
        driver = uc.Chrome(options=ch_opt,use_subprocess=True)
        driver.maximize_window()
        return driver

    def get_videos(self):
        flag1 = 'a=1988'
        flag2 = 'mime_type=video_mp4'
        driver = self.get_driver()
        action = ActionChains(driver)
        driver.get(self.url)
        while True:
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            videos = driver.find_elements(by=By.XPATH,value=f"//a[contains(@href, 'www.tiktok.com/@{self.username}/video/')]")
            self.sleep_it()
            new_videos = driver.find_elements(by=By.XPATH,value=f"//a[contains(@href, 'www.tiktok.com/@{self.username}/video/')]")
            if len(videos) == len(new_videos):
                break
            else:
                if self.count <= self.limit:
                    self.count +=1
                    continue
                else:
                    break
        for video in new_videos:
            action.move_to_element(video).perform()
            self.sleep_it()
        temp_urls = []
        for request in driver.requests:
            if flag1 in request.url and flag2 in request.url:
                if self.counter <= self.limit and self.db(lookup={"url":request.url,'upload':None}):
                    self.counter+=1
                    temp_urls.append(request.url)
                    # self.db(store={"url":request.url})
                else:
                    break
        self.counter = 0
        temp_meta = []
        sel = scrapy.Selector(text=driver.page_source)
        for meta in sel.xpath("//div[contains(@class,'DivTagCardDesc')]/a/@title").getall():
            if self.counter <= self.limit:
                temp_meta.append(meta)

        # mapping
        video_dict = {}
        for video,meta in zip(temp_urls,temp_meta):
            self.db(store={'url':video,"meta":meta,'upload':None})
            video_dict[video] = meta
        driver.close()

        # downloading
        self.counter = 0
        print(" [+] Downloading Started")
        for data in self.db(get={'upload':None})[:self.limit]:
            # data is tuple (url,meta)
            url = data[0]
            self.counter+=1
            self.download_it(url=url, filename=self.counter)
            print(f"\r [+] Downloaded video {self.counter} ",end='')

    def download_it(self,url,filename):
        ydl_opts = {
                'outtmpl': f'ready_to_upload\\{self.username}_{filename}.mp4',
                'ignoreerrors': True,
            }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def sleep_it(self,custom=None):
        r = []
        if custom:
            min = custom['min']
            max = custom['max']
            for i in range(min,max):
                r.append(i)
            time.sleep(random.choice(r))
        else:
            for i in range(self.min,self.max):
                r.append(i)
            time.sleep(random.choice(r))

    def upload(self):
        driver = self.get_driver()
        for data in self.db(get={'upload': None})[:self.limit]:
            url = data[0]
            if self.db(lookup={'url': url, 'upload': True}):
                meta = data[1]
                filename = self.counter
                url = 'https://studio.youtube.com/channel/UCcF2MpZNT2MeSsN2H-K1gQA/videos/upload?d=ud&filter=%5B%5D&sort=%7B%22columnType%22%3A%22date%22%2C%22sortOrder%22%3A%22DESCENDING%22%7D'
                driver.get(url)
                driver.find_element(by=By.XPATH, value="//input[@type='file']").send_keys(f"ready_to_upload\\{self.username}_{filename}.mp4")
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH,value="//div[@id='textbox' and contains(@aria-label,'title')]").send_keys(f" {meta}")
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH,value="//div[@id='textbox' and contains(@aria-label,'viewers')]").send_keys(f"{meta} \nCredit: {self.username}")
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH,value="//tp-yt-paper-radio-button[@name='VIDEO_MADE_FOR_KIDS_NOT_MFK'] //div[@id='offRadio']").click()
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH, value="//div[contains(text(),'Next')]").click()
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH, value="//div[contains(text(),'Next')]").click()
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH, value="//div[contains(text(),'Next')]").click()
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH, value="//tp-yt-paper-radio-button[@name='PUBLIC']").click()
                self.sleep_it(custom={"min": 5, "max": 7})
                driver.find_element(by=By.XPATH, value="//ytcp-button/div[contains(text(),'Publish')]").click()
                time.sleep(10)
                self.counter += 1
                self.db(store={'url': url, 'upload': True})
        driver.close()


def start():
    username = input("\n [+] Enter Username: ")
    limit = int(input(" [+] Videos Count: "))
    tik = TikYou(username, limit)
    script_mode = int(input("\n 1. Download\n 2. Upload\n\n [+] Select from above: "))
    if script_mode == 1:
        try:
            print(" [!] Downloading..")
            tik.get_videos()
        except Exception as e:
            # print(e)
            print(" [!] Internet Issue Detected")
        else:
            print(" [!] Finished")
    elif script_mode == 2:
        try:
            print(" [!] Uploading..")
            tik.upload()
        except Exception as e:
            # print(e)
            print(" [!] Internet Issue Detected")
        else:
            print(" [!] Finished")


if __name__ == "__main__":
    try:
        subprocess.call("TASKKILL /f /IM CHROME.EXE",stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except:
        pass
    else:
        pass
    finally:
        start()

# tariqjameel2126
