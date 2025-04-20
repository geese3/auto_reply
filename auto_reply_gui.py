import sys
import os
import time
import random
import re
import requests
import platform
import json
import pyperclip
from bs4 import BeautifulSoup
from typing import Optional, Tuple, List
from dotenv import load_dotenv
import google.generativeai as genai
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
from threading import Event

class NaverBot:
    def __init__(self, id, pw, nickname, use_gemini, start_page, end_page, log_callback=None, stop_flag=None):
        load_dotenv()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.cookies = {}
        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        }
        self.driver = None
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.comment_templates = [
            "좋은 글 잘 읽었습니다. 감사합니다!",
            "유익한 정보 감사합니다. 잘 보고 갑니다!",
            "정말 도움이 되는 글이네요. 공감합니다!",
            "글 잘 읽었습니다. 다음 글도 기대됩니다!",
            "좋은 정보 공유해주셔서 감사합니다!"
        ]
        self.current_template_index = 0
        self.id = id
        self.pw = pw
        self.nickname = nickname
        self.use_gemini = use_gemini
        self.start_page = start_page
        self.end_page = end_page
        self.log_callback = log_callback
        self.stop_flag = stop_flag

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def should_stop(self):
        return self.stop_flag and self.stop_flag.is_set()

    def initialize_driver(self):
        if self.driver:
            return
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.driver = uc.Chrome(options=options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

    def login(self):
        try:
            self.log("네이버 로그인 페이지 접속...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(random.uniform(2, 4))
            id_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_id"))
            )
            time.sleep(random.uniform(1, 2))
            self.copy_paste_text(id_input, self.id)
            pw_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_pw"))
            )
            time.sleep(random.uniform(1, 2))
            self.copy_paste_text(pw_input, self.pw)
            login_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "log.login"))
            )
            time.sleep(random.uniform(1, 2))
            login_button.click()
            time.sleep(random.uniform(3, 5))
            try:
                current_title = self.driver.title
                if current_title and "로그인" in current_title:
                    self.log("캡차나 보안 문제가 발생했습니다. 브라우저에서 직접 로그인 후 엔터를 눌러주세요.")
                    input()
            except Exception:
                pass
            return True
        except Exception as e:
            self.log(f"로그인 중 오류 발생: {str(e)}")
            return False

    def wait_random_time(self, min_seconds: float, max_seconds: float):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def process_pages(self):
        try:
            total_processed = 0
            for page in range(self.start_page, self.end_page + 1):
                if self.should_stop():
                    self.log("작업이 중지되었습니다.")
                    break
                self.log(f"\n=== {page}페이지 처리 시작 ===")
                neighbor_blogs = self.get_neighbor_blogs(page)
                if not neighbor_blogs:
                    self.log(f"{page}페이지의 이웃 블로그 목록을 가져오는데 실패했습니다.")
                    break  # break로 반복문 즉시 종료
                self.log(f"총 {len(neighbor_blogs)}개의 이웃 블로그를 찾았습니다.")
                for blog_id, blog_post_id in neighbor_blogs:
                    if self.should_stop():
                        self.log("작업이 중지되었습니다.")
                        break
                    self.log(f"\n처리 중: {blog_id}의 포스트 {blog_post_id}")
                    self.like_post(blog_id, blog_post_id)
                    self.wait_random_time(2, 4)
                    try:
                        self.write_comment(blog_id, blog_post_id)
                    except Exception as e:
                        self.log(f"댓글 작성 중 오류 발생: {str(e)}")
                    total_processed += 1
                    self.wait_random_time(3, 5)
                self.log(f"\n{page}페이지 처리가 완료되었습니다.")
                if page < self.end_page:
                    self.log(f"\n{page+1}페이지 처리 전 대기 중...")
                    self.wait_random_time(5, 7)
            self.log(f"\n모든 처리가 완료되었습니다. 총 {total_processed}개의 포스트를 처리했습니다.")
        except Exception as e:
            self.log(f"페이지 처리 중 오류 발생: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None  # quit 후 driver 참조 방지
                self.log("\n웹드라이버가 종료되었습니다.")

    def get_cbox_token(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        try:
            url = "https://apis.naver.com/commentBox/cbox/web_naver_token_jsonp.json"
            params = {
                'ticket': 'blog',
                'templateId': 'default',
                'pool': 'blogid',
                'lang': 'ko',
                'country': '',
                'objectId': f'154352947_201_{blog_post_id}',
                '_cv': '20240923174033',
                'categoryId': '',
                'groupId': '154352947',
            }
            headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': 'https://m.blog.naver.com/CommentList.naver',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'script',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            response = session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()['result']['cbox_token']
        except Exception as e:
            self.log(f"cbox_token 가져오기 실패: {str(e)}")
            return None

    def get_blog_no(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        try:
            url = f'https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={blog_post_id}'
            response = requests.get(url)
            response.raise_for_status()
            content = response.content.decode('utf-8')
            match = re.search(r"blogNo\s*=\s*'(\d+)'", content)
            return match.group(1) if match else None
        except Exception as e:
            self.log(f"블로그 번호 가져오기 실패: {str(e)}")
            return None

    def get_blog_content(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        try:
            url = f'https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={blog_post_id}'
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.find('div', {'class': 'se-main-container'})
            if not content:
                content = soup.find('div', {'id': 'postViewArea'})
            if content:
                text = content.get_text(separator=' ', strip=True)
                return text[:2000]
            return None
        except Exception as e:
            self.log(f"블로그 내용 가져오기 실패: {str(e)}")
            return None

    def generate_comment_with_gemini(self, blog_content: str) -> Optional[str]:
        try:
            prompt = f"""
            다음 블로그 글을 읽고 적절한 댓글을 작성해주세요.
            댓글은 1-2문장으로 간단하게 작성하고, 블로그 내용을 잘 이해했다는 것을 보여주면서
            긍정적이고 격려하는 톤으로 작성해주세요.
            블로그 내용:
            {blog_content}
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            self.log(f"Gemini 댓글 생성 실패: {str(e)}")
            return None

    def has_commented(self, blog_id: str, blog_post_id: str) -> bool:
        try:
            blog_Num = self.get_blog_no(blog_id, blog_post_id)
            if not blog_Num:
                self.log("블로그 번호를 가져오지 못했습니다.")
                return False
            url = f"https://apis.naver.com/commentBox/cbox/web_naver_list_json.json"
            params = {
                'ticket': 'blog',
                'templateId': 'default',
                'pool': 'blogid',
                'lang': 'ko',
                'country': '',
                'objectId': f'{blog_Num}_201_{blog_post_id}',
                'categoryId': '',
                'pageSize': '100',
                'indexSize': '10',
                'groupId': blog_Num,
                'listType': 'OBJECT',
                'pageType': 'more',
                'objectUrl': f'https://m.blog.naver.com/CommentList.naver?blogId={blog_id}&logNo={blog_post_id}',
                '_cv': str(int(time.time() * 1000))
            }
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': f'https://m.blog.naver.com/CommentList.naver?blogId={blog_id}&logNo={blog_post_id}',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            response = session.get(url, params=params, headers=headers)
            result = response.json()
            if 'result' in result and 'commentList' in result['result']:
                for comment in result['result']['commentList']:
                    if comment.get('userName') == self.nickname:
                        self.log(f"이미 '{self.nickname}' 님이 댓글을 작성하셨습니다.")
                        return True
            return False
        except Exception as e:
            self.log(f"댓글 목록 확인 중 오류 발생: {str(e)}")
            return False

    def write_comment(self, blog_id: str, blog_post_id: str) -> bool:
        try:
            if self.has_commented(blog_id, blog_post_id):
                self.log("이미 댓글을 작성한 포스트입니다.")
                return False
            if self.use_gemini:
                blog_content = self.get_blog_content(blog_id, blog_post_id)
                if not blog_content:
                    self.log("블로그 내용을 가져오지 못했습니다.")
                    return False
                comment_content = self.generate_comment_with_gemini(blog_content)
                if not comment_content:
                    self.log("댓글 생성에 실패했습니다.")
                    return False
            else:
                comment_content = self.comment_templates[self.current_template_index]
                self.current_template_index = (self.current_template_index + 1) % len(self.comment_templates)
            blog_Num = self.get_blog_no(blog_id, blog_post_id)
            if not blog_Num:
                self.log("블로그 번호를 가져오지 못했습니다.")
                return False
            cbox_token = self.get_cbox_token(blog_id, blog_post_id)
            if not cbox_token:
                self.log("cbox_token을 가져오지 못했습니다.")
                return False
            url = "https://apis.naver.com/commentBox/cbox/web_naver_create_json.json"
            params = {
                'ticket': 'blog',
                'templateId': 'default',
                'pool': 'blogid',
                '_cv': str(int(time.time() * 1000))
            }
            data = {
                'lang': 'ko',
                'country': '',
                'objectId': f'{blog_Num}_201_{blog_post_id}',
                'categoryId': '',
                'pageSize': '100',
                'indexSize': '10',
                'groupId': f'{blog_Num}',
                'listType': 'OBJECT',
                'pageType': 'more',
                'objectUrl': f'https://m.blog.naver.com/CommentList.naver?blogId={blog_id}&logNo={blog_post_id}',
                'contents': comment_content,
                'userType': '',
                'pick': 'false',
                'manager': 'false',
                'score': '0',
                'sort': 'NEW',
                'secret': 'false',
                'refresh': 'false',
                'imageCount': '0',
                'commentType': 'txt',
                'validateBanWords': 'false',
                'cbox_token': cbox_token
            }
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'origin': 'https://m.blog.naver.com',
                'referer': f'https://m.blog.naver.com/CommentList.naver?blogId={blog_id}&logNo={blog_post_id}',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded'
            }
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            response = session.post(url, params=params, headers=headers, data=data)
            result = response.json()
            if 'success' in result and result['success']:
                self.log("댓글 작성 성공!")
                return True
            else:
                self.log("댓글 작성 실패")
                return False
        except Exception as e:
            self.log(f"댓글 작성 중 오류 발생: {str(e)}")
            return False

    def get_like_tokens(self, blog_id: str, blog_post_id: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            url = "https://apis.naver.com/blogserver/like/v1/search/contents"
            params = {
                'suppress_response_codes': 'true',
                'pool': 'blogid',
                'q': f'BLOG[{blog_id}_{blog_post_id}]',
                'isDuplication': 'true',
                'cssIds': 'BASIC_MOBILE,BLOG_MOBILE',
            }
            response = requests.get(url, params=params, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            data = response.json()
            return data.get('timestamp'), data.get('guestToken')
        except Exception as e:
            self.log(f"좋아요 토큰 가져오기 실패: {str(e)}")
            return None, None

    def like_post(self, blog_id: str, blog_post_id: str) -> bool:
        try:
            token_url = "https://apis.naver.com/blogserver/like/v1/search/contents"
            token_params = {
                'suppress_response_codes': 'true',
                'pool': 'blogid',
                'q': f'BLOG[{blog_id}_{blog_post_id}]',
                'isDuplication': 'true',
                'cssIds': 'BASIC_MOBILE,BLOG_MOBILE',
            }
            token_headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': 'https://m.blog.naver.com/PostView.naver',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'script',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            self.log("\ntimestamp와 guestToken 가져오는 중...")
            token_response = session.get(token_url, params=token_params, headers=token_headers)
            token_result = token_response.json()
            timestamp = token_result.get('timestamp')
            guest_token = token_result.get('guestToken')
            if not timestamp or not guest_token:
                self.log("timestamp 또는 guestToken을 가져오지 못했습니다.")
                return False
            url = f"https://apis.naver.com/blogserver/like/v1/services/BLOG/contents/{blog_id}_{blog_post_id}"
            self.log(f"좋아요 API URL: {url}")
            params = {
                'suppress_response_codes': 'true',
                '_method': 'POST',
                'pool': 'blogid',
                'displayId': 'BLOG',
                'reactionType': 'like',
                'categoryId': 'post',
                'guestToken': guest_token,
                'timestamp': timestamp,
                '_ch': 'mbw',
                'isDuplication': 'true',
                'lang': 'ko',
                'countType': 'DEFAULT',
                'count': '1',
                'history': '',
                'runtimeStatus': '',
                'isPostTimeline': 'false',
                '_': timestamp
            }
            headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': 'https://m.blog.naver.com/PostView.naver',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'script',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            }
            self.log("\n좋아요 요청 전송 중...")
            response = session.get(url, params=params, headers=headers)
            self.log(f"응답 상태 코드: {response.status_code}")
            result = response.json()
            if 'statusCode' in result:
                if result['statusCode'] == 200 or (result['statusCode'] == 409 and result['message'] == '이미 공감한 컨텐츠입니다.'):
                    self.log(f"이미 이 포스트에 공감을 하셨습니다.")
                    return True
                else:
                    self.log(f"좋아요 실패: {result.get('message', '알 수 없는 오류')}")
                    return False
            elif 'isReacted' in result and result['isReacted']:
                self.log(f"좋아요 성공! 현재 좋아요 수: {result['count']}")
                return True
            else:
                self.log("좋아요 실패: 응답 형식이 예상과 다릅니다.")
                return False
        except Exception as e:
            self.log(f"좋아요 실패: {str(e)}")
            self.log(f"상세 오류: {e.__class__.__name__}")
            return False

    def copy_paste_text(self, element, text):
        pyperclip.copy(text)
        time.sleep(0.5)
        element.click()
        time.sleep(0.5)
        if platform.system() == 'Darwin':
            actions = ActionChains(self.driver)
            actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND)
            actions.perform()
        else:
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
            actions.perform()
        time.sleep(0.5)

    def get_neighbor_blogs(self, page: int = 1) -> List[Tuple[str, str]]:
        """이웃새글 목록을 가져옵니다."""
        try:
            self.log(f"6. 네이버 블로그 홈페이지로 이동 (페이지 {page})...")
            self.driver.get(f"https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage={page}&groupId=0")
            time.sleep(5)  # 페이지 로딩 대기

            self.log("7. 이웃새글 목록 로드 대기...")
            wait = WebDriverWait(self.driver, 15)
            buddy_section = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'section.wrap_thumbnail_post_list'))
            )

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 이웃새글 섹션 내의 게시물 모두 선택 (multi_pic, 일반 item 모두)
            posts = buddy_section.find_elements(By.CSS_SELECTOR, 'div.item')
            self.log(f"8. 찾은 이웃 게시물 수: {len(posts)}")

            blog_links = []
            seen_urls = set()
            self.log("9. 게시물 정보 추출 시작...")
            for i, post in enumerate(posts, 1):
                try:
                    self.log(f"\n게시물 {i} 처리 중...")
                    post_link = post.find_element(By.CSS_SELECTOR, 'a.desc_inner')
                    href = post_link.get_attribute('href')
                    self.log(f"  - href: {href}")
                    # 두 가지 패턴 모두 지원
                    match = re.search(r'blogId=([\w\d_-]*)&logNo=(\d+)', href)
                    if not match:
                        match = re.search(r'/([\w\d_-]+)/([0-9]+)$', href)
                    if match:
                        if len(match.groups()) == 2:
                            blog_id = match.group(1)
                            blog_post_id = match.group(2)
                            self.log(f"  - blog_id: {blog_id}, blog_post_id: {blog_post_id}")
                            if href not in seen_urls:
                                blog_links.append((blog_id, blog_post_id))
                                seen_urls.add(href)
                        else:
                            self.log(f"  - 정규식 매칭 실패: {href}")
                    else:
                        self.log(f"  - 정규식 매칭 실패: {href}")
                except Exception as e:
                    self.log(f"게시물 {i} 처리 중 오류 발생: {str(e)}")
                    continue
            # 최대 10개로 제한
            result_links = blog_links[:10]
            self.log(f"\n이웃새글 {len(result_links)}개를 찾았습니다.")
            return result_links
        except Exception as e:
            self.log(f"이웃새글 목록을 가져오는 중 오류 발생: {str(e)}")
            self.log(f"상세 오류: {e.__class__.__name__}")
            return []

class BotThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    def __init__(self, id, pw, nickname, use_gemini, start_page, end_page):
        super().__init__()
        from threading import Event
        self.id = id
        self.pw = pw
        self.nickname = nickname
        self.use_gemini = use_gemini
        self.start_page = start_page
        self.end_page = end_page
        self._stop_flag = Event()
    def run(self):
        try:
            bot = NaverBot(self.id, self.pw, self.nickname, self.use_gemini, self.start_page, self.end_page, log_callback=self.log_signal.emit, stop_flag=self._stop_flag)
            bot.initialize_driver()
            if not bot.login():
                self.log_signal.emit("로그인에 실패했습니다. 프로그램을 종료합니다.")
                return
            bot.process_pages()
        except Exception as e:
            self.log_signal.emit(f"오류 발생: {str(e)}")
        finally:
            self.finished_signal.emit()
    def stop(self):
        self._stop_flag.set()

class MainWindow(QMainWindow):
    SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 블로그 자동 댓글 프로그램")
        self.setGeometry(100, 100, 800, 600)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        input_group = QWidget()
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)
        id_layout = QHBoxLayout()
        id_label = QLabel("네이버 아이디:")
        self.id_input = QLineEdit()
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.id_input)
        input_layout.addLayout(id_layout)
        pw_layout = QHBoxLayout()
        pw_label = QLabel("네이버 비밀번호:")
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)
        pw_layout.addWidget(pw_label)
        pw_layout.addWidget(self.pw_input)
        input_layout.addLayout(pw_layout)
        nickname_layout = QHBoxLayout()
        nickname_label = QLabel("확인할 닉네임:")
        self.nickname_input = QLineEdit()
        nickname_layout.addWidget(nickname_label)
        nickname_layout.addWidget(self.nickname_input)
        input_layout.addLayout(nickname_layout)
        comment_type_layout = QHBoxLayout()
        comment_type_label = QLabel("댓글 생성 방식:")
        self.comment_type_combo = QComboBox()
        self.comment_type_combo.addItems(["템플릿 댓글", "Gemini AI 댓글"])
        comment_type_layout.addWidget(comment_type_label)
        comment_type_layout.addWidget(self.comment_type_combo)
        input_layout.addLayout(comment_type_layout)
        page_range_layout = QHBoxLayout()
        start_label = QLabel("시작 페이지:")
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setRange(1, 100)
        self.start_page_spin.setValue(1)
        end_label = QLabel("끝 페이지:")
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setRange(1, 100)
        self.end_page_spin.setValue(1)
        page_range_layout.addWidget(start_label)
        page_range_layout.addWidget(self.start_page_spin)
        page_range_layout.addWidget(end_label)
        page_range_layout.addWidget(self.end_page_spin)
        input_layout.addLayout(page_range_layout)
        layout.addWidget(input_group)
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("실행")
        self.start_btn.clicked.connect(self.start_bot)
        btn_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_bot)
        btn_layout.addWidget(self.stop_btn)
        self.save_btn = QPushButton("설정 저장")
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        self.bot_thread = None
        self.load_settings()

    def save_settings(self):
        settings = {
            "id": self.id_input.text().strip(),
            "pw": self.pw_input.text().strip(),
            "nickname": self.nickname_input.text().strip(),
            "comment_type": self.comment_type_combo.currentIndex(),
            "start_page": self.start_page_spin.value(),
            "end_page": self.end_page_spin.value()
        }
        try:
            with open(self.SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", f"설정 저장 중 오류: {str(e)}")

    def load_settings(self):
        if not os.path.exists(self.SETTINGS_PATH):
            return
        try:
            with open(self.SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.id_input.setText(settings.get("id", ""))
            self.pw_input.setText(settings.get("pw", ""))
            self.nickname_input.setText(settings.get("nickname", ""))
            self.comment_type_combo.setCurrentIndex(settings.get("comment_type", 0))
            self.start_page_spin.setValue(settings.get("start_page", 1))
            self.end_page_spin.setValue(settings.get("end_page", 1))
        except Exception as e:
            QMessageBox.warning(self, "불러오기 실패", f"설정 불러오기 중 오류: {str(e)}")

    def start_bot(self):
        id = self.id_input.text().strip()
        pw = self.pw_input.text().strip()
        nickname = self.nickname_input.text().strip()
        use_gemini = self.comment_type_combo.currentIndex() == 1
        start_page = self.start_page_spin.value()
        end_page = self.end_page_spin.value()
        if not id or not pw or not nickname:
            QMessageBox.warning(self, "입력 오류", "아이디, 비밀번호, 닉네임을 모두 입력해주세요.")
            return
        if start_page > end_page:
            QMessageBox.warning(self, "입력 오류", "시작 페이지는 끝 페이지보다 작거나 같아야 합니다.")
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_text.clear()
        self.bot_thread = BotThread(id, pw, nickname, use_gemini, start_page, end_page)
        self.bot_thread.log_signal.connect(self.append_log)
        self.bot_thread.finished_signal.connect(self.bot_finished)
        self.bot_thread.start()

    def stop_bot(self):
        if self.bot_thread:
            self.append_log("중지 요청됨: 현재 작업이 안전하게 중단됩니다.")
            self.bot_thread.stop()
            self.stop_btn.setEnabled(False)

    def append_log(self, msg):
        self.log_text.append(msg)
        self.log_text.ensureCursorVisible()

    def bot_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "완료", "작업이 완료되었습니다.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
