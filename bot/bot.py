import pyperclip
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

class NaverBot:
    def __init__(self, id, pw, os:str = 'window', msg: str = "", relKeywords: list = [], searchNum=1000, delay=1, searchOption="sim"):
        self.os = os
        self.id = id
        self.pw = pw
        self.msg = msg
        self.relKeywords = relKeywords
        self.delay = delay
        self.searchNum = searchNum
        self.searchOption = searchOption
        self.tmp_info = defaultdict(list)
        self.tmp_key_id = defaultdict(dict)
        self.headers = {
            "Authority": "section.blog.naver.com",
            "Method": "GET",
            "Scheme": "https",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

    def login_naver(self):
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

        url = 'https://nid.naver.com/nidlogin.login'
        self.driver.get(url)
        self.driver.implicitly_wait(10)

        if self.os == 'window':
            paste_keys = Keys.CONTROL + 'V'
        else:
            paste_keys = Keys.COMMAND + 'V'

        pyperclip.copy(self.id)
        self.driver.find_element(By.XPATH, '//*[@id="id"]').send_keys(paste_keys)
        pyperclip.copy(self.pw)
        self.driver.find_element(By.XPATH, '//*[@id="pw"]').send_keys(paste_keys)

        self.driver.implicitly_wait(10)
        self.driver.find_element(By.ID, 'log.login').click()
        self.driver.implicitly_wait(10)

        cookies = self.driver.get_cookies()
        self.naver_cookie = defaultdict(str)
        for cookie in cookies:
            self.naver_cookie[cookie['name']] = cookie['value']
        
        self.driver.close()