import os
import time
import requests
import re
import google.generativeai as genai
from bs4 import BeautifulSoup
from typing import Optional, Dict, Tuple, List
from dotenv import load_dotenv
from collections import defaultdict
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import platform
import undetected_chromedriver as uc
import pyperclip
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import json

class NaverBot:
    def __init__(self):
        """NaverBot 초기화"""
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
        
        # Gemini API 설정
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 댓글 템플릿
        self.comment_templates = [
            "좋은 글 잘 읽었습니다. 감사합니다!",
            "유익한 정보 감사합니다. 잘 보고 갑니다!",
            "정말 도움이 되는 글이네요. 공감합니다!",
            "글 잘 읽었습니다. 다음 글도 기대됩니다!",
            "좋은 정보 공유해주셔서 감사합니다!"
        ]
        self.current_template_index = 0
        
        # 로그인 정보 및 페이지 수 입력
        print("\n=== 네이버 로그인 정보 입력 ===")
        self.id = input("네이버 아이디를 입력하세요: ")
        self.pw = input("네이버 비밀번호를 입력하세요: ")
        self.nickname = input("확인할 닉네임을 입력하세요: ")
        
        # 댓글 생성 방식 선택
        while True:
            try:
                print("\n=== 댓글 생성 방식 선택 ===")
                print("1. 템플릿 댓글 사용 (미리 정의된 댓글을 순서대로 사용)")
                print("2. Gemini AI 사용 (블로그 내용을 분석하여 댓글 생성)")
                comment_type = int(input("댓글 생성 방식을 선택하세요 (1 또는 2): "))
                if comment_type in [1, 2]:
                    self.use_gemini = (comment_type == 2)
                    break
                else:
                    print("1 또는 2를 입력해주세요.")
            except ValueError:
                print("올바른 숫자를 입력해주세요.")
        
        # 페이지 수 입력
        while True:
            try:
                self.max_pages = int(input("몇 페이지까지 처리할까요? (1-10): "))
                if 1 <= self.max_pages <= 10:
                    break
                else:
                    print("1에서 10 사이의 숫자를 입력해주세요.")
            except ValueError:
                print("올바른 숫자를 입력해주세요.")
        print("===========================\n")
        
        # 웹드라이버 초기화 및 로그인
        self.initialize_driver()
        if not self.login():
            print("로그인에 실패했습니다. 프로그램을 종료합니다.")
            if self.driver:
                self.driver.quit()
            return
            
        # 페이지 처리 시작
        self.process_pages()

    def initialize_driver(self):
        """웹드라이버 초기화"""
        if self.driver:
            return
            
        print("1. 웹드라이버 설정 시작...")
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
        
        print("2. 웹드라이버 초기화...")
        self.driver = uc.Chrome(options=options)
        
        # 자동화 감지 방지 스크립트 실행
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

    def login(self):
        """네이버 로그인"""
        try:
            print("3. 네이버 로그인 페이지 접속...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(random.uniform(2, 4))
            
            print("4. 로그인 정보 입력...")
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
            
            print("5. 로그인 버튼 클릭...")
            login_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "log.login"))
            )
            time.sleep(random.uniform(1, 2))
            login_button.click()
            time.sleep(random.uniform(3, 5))
            
            # 로그인 성공 확인
            try:
                current_title = self.driver.title
                if current_title and "로그인" in current_title:
                    print("\n[알림] 캡차나 보안 문제가 발생했습니다.")
                    print("브라우저에서 직접 로그인을 진행해주세요.")
                    print("로그인이 완료되면 아무 키나 눌러주세요...")
                    try:
                        input()
                        print("로그인 완료를 확인했습니다. 계속 진행합니다...")
                    except KeyboardInterrupt:
                        print("\n프로그램을 종료합니다.")
                        self.driver.quit()
                        return False
            except Exception as e:
                print("\n[알림] 로그인 상태 확인 중 문제가 발생했습니다.")
                print("브라우저에서 직접 로그인을 진행해주세요.")
                print("로그인이 완료되면 아무 키나 눌러주세요...")
                try:
                    input()
                    print("로그인 완료를 확인했습니다. 계속 진행합니다...")
                except KeyboardInterrupt:
                    print("\n프로그램을 종료합니다.")
                    self.driver.quit()
                    return False
                    
            return True
            
        except Exception as e:
            print(f"로그인 중 오류 발생: {str(e)}")
            return False

    def wait_random_time(self, min_seconds: float, max_seconds: float):
        """랜덤 대기 시간 설정"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def process_pages(self) -> None:
        """프로그램 실행"""
        try:
            total_processed = 0
            
            for page in range(1, self.max_pages + 1):
                print(f"\n=== {page}페이지 처리 시작 ===")
                
                # 이웃 블로그 목록 가져오기
                neighbor_blogs = self.get_neighbor_blogs(page)
                if not neighbor_blogs:
                    print(f"{page}페이지의 이웃 블로그 목록을 가져오는데 실패했습니다.")
                    break  # 실패하면 더 이상 진행하지 않음
                
                print(f"총 {len(neighbor_blogs)}개의 이웃 블로그를 찾았습니다.")
                
                # 각 블로그 포스트에 대해 처리
                for blog_id, blog_post_id in neighbor_blogs:
                    print(f"\n처리 중: {blog_id}의 포스트 {blog_post_id}")
                    
                    # 좋아요
                    self.like_post(blog_id, blog_post_id)
                    self.wait_random_time(2, 4)
                    
                    # 댓글 작성
                    try:
                        self.write_comment(blog_id, blog_post_id)
                    except Exception as e:
                        print(f"댓글 작성 중 오류 발생: {str(e)}")
                        
                    total_processed += 1
                    self.wait_random_time(3, 5)
                
                print(f"\n{page}페이지 처리가 완료되었습니다.")
                
                # 페이지가 1이면 여기서 종료
                if self.max_pages == 1:
                    break
                
                # 다음 페이지 처리 전 대기
                if page < self.max_pages:
                    print(f"\n{page+1}페이지 처리 전 대기 중...")
                    self.wait_random_time(5, 7)
            
            print(f"\n모든 처리가 완료되었습니다. 총 {total_processed}개의 포스트를 처리했습니다.")
            
        except Exception as e:
            print(f"페이지 처리 중 오류 발생: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                print("\n웹드라이버가 종료되었습니다.")

    def get_cbox_token(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        """댓글 작성을 위한 cbox_token을 가져옵니다."""
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
            print(f"cbox_token 가져오기 실패: {str(e)}")
            return None
            
    def get_blog_no(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        """블로그 번호를 가져옵니다."""
        try:
            url = f'https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={blog_post_id}'
            response = requests.get(url)
            response.raise_for_status()
            
            content = response.content.decode('utf-8')
            match = re.search(r"blogNo\s*=\s*'(\d+)'", content)
            
            return match.group(1) if match else None
            
        except Exception as e:
            print(f"블로그 번호 가져오기 실패: {str(e)}")
            return None
            
    def get_blog_content(self, blog_id: str, blog_post_id: str) -> Optional[str]:
        """블로그 포스트의 내용을 가져옵니다."""
        try:
            url = f'https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={blog_post_id}'
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 블로그 내용 추출
            content = soup.find('div', {'class': 'se-main-container'})
            if not content:
                content = soup.find('div', {'id': 'postViewArea'})
                
            if content:
                # 텍스트만 추출
                text = content.get_text(separator=' ', strip=True)
                return text[:2000]  # Gemini API 토큰 제한을 고려하여 내용 제한
            return None
            
        except Exception as e:
            print(f"블로그 내용 가져오기 실패: {str(e)}")
            return None
            
    def generate_comment_with_gemini(self, blog_content: str) -> Optional[str]:
        """Gemini API를 사용하여 블로그 내용에 맞는 댓글을 생성합니다."""
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
            print(f"Gemini 댓글 생성 실패: {str(e)}")
            return None
            
    def has_commented(self, blog_id: str, blog_post_id: str) -> bool:
        """이미 댓글을 작성했는지 확인합니다."""
        try:
            # 블로그 번호 가져오기
            blog_Num = self.get_blog_no(blog_id, blog_post_id)
            if not blog_Num:
                print("블로그 번호를 가져오지 못했습니다.")
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
                        print(f"이미 '{self.nickname}' 님이 댓글을 작성하셨습니다.")
                        return True
                            
            return False
            
        except Exception as e:
            print(f"댓글 목록 확인 중 오류 발생: {str(e)}")
            return False

    def write_comment(self, blog_id: str, blog_post_id: str) -> bool:
        """블로그에 댓글을 작성합니다."""
        try:
            # 이미 댓글을 작성했는지 확인
            if self.has_commented(blog_id, blog_post_id):
                print("이미 댓글을 작성한 포스트입니다.")
                return False
                
            # 댓글 내용 생성
            if self.use_gemini:
                # Gemini API로 댓글 생성
                blog_content = self.get_blog_content(blog_id, blog_post_id)
                if not blog_content:
                    print("블로그 내용을 가져오지 못했습니다.")
                    return False
                    
                comment_content = self.generate_comment_with_gemini(blog_content)
                if not comment_content:
                    print("댓글 생성에 실패했습니다.")
                    return False
            else:
                # 템플릿 댓글 사용
                comment_content = self.comment_templates[self.current_template_index]
                self.current_template_index = (self.current_template_index + 1) % len(self.comment_templates)
                
            # 댓글 작성 API 호출
            blog_Num = self.get_blog_no(blog_id, blog_post_id)
            if not blog_Num:
                print("블로그 번호를 가져오지 못했습니다.")
                return False
                
            cbox_token = self.get_cbox_token(blog_id, blog_post_id)
            if not cbox_token:
                print("cbox_token을 가져오지 못했습니다.")
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
                print("댓글 작성 성공!")
                return True
            else:
                print("댓글 작성 실패")
                return False
                
        except Exception as e:
            print(f"댓글 작성 중 오류 발생: {str(e)}")
            return False
            
    def get_like_tokens(self, blog_id: str, blog_post_id: str) -> Tuple[Optional[str], Optional[str]]:
        """좋아요를 위한 timestamp와 guestToken을 가져옵니다."""
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
            print(f"좋아요 토큰 가져오기 실패: {str(e)}")
            return None, None
            
    def like_post(self, blog_id: str, blog_post_id: str) -> bool:
        """블로그 포스트에 좋아요를 누릅니다."""
        try:
            # timestamp와 guestToken 가져오기
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
            
            # 세션 생성 및 쿠키 설정
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            
            # timestamp와 guestToken 가져오기
            print("\ntimestamp와 guestToken 가져오는 중...")
            token_response = session.get(token_url, params=token_params, headers=token_headers)
            token_result = token_response.json()
            
            timestamp = token_result.get('timestamp')
            guest_token = token_result.get('guestToken')
            
            if not timestamp or not guest_token:
                print("timestamp 또는 guestToken을 가져오지 못했습니다.")
                return False
            
            # 좋아요 API URL
            url = f"https://apis.naver.com/blogserver/like/v1/services/BLOG/contents/{blog_id}_{blog_post_id}"
            print(f"좋아요 API URL: {url}")
            
            # 요청 파라미터
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
            
            # 요청 헤더
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
            
            # 좋아요 요청 보내기
            print("\n좋아요 요청 전송 중...")
            response = session.get(url, params=params, headers=headers)
            print(f"응답 상태 코드: {response.status_code}")
            
            # 응답 확인
            result = response.json()
            
            # 응답 형식 확인
            if 'statusCode' in result:
                if result['statusCode'] == 200 or (result['statusCode'] == 409 and result['message'] == '이미 공감한 컨텐츠입니다.'):
                    print(f"이미 이 포스트에 공감을 하셨습니다.")
                    return True
                else:
                    print(f"좋아요 실패: {result.get('message', '알 수 없는 오류')}")
                    return False
            elif 'isReacted' in result and result['isReacted']:
                print(f"좋아요 성공! 현재 좋아요 수: {result['count']}")
                return True
            else:
                print("좋아요 실패: 응답 형식이 예상과 다릅니다.")
                return False
            
        except Exception as e:
            print(f"좋아요 실패: {str(e)}")
            print(f"상세 오류: {e.__class__.__name__}")
            return False
            
    def copy_paste_text(self, element, text):
        """OS에 따라 다른 단축키로 텍스트를 복사/붙여넣기하는 함수"""
        pyperclip.copy(text)
        time.sleep(0.5)
        
        element.click()
        time.sleep(0.5)
        
        if platform.system() == 'Darwin':  # Mac OS
            actions = ActionChains(self.driver)
            actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND)
            actions.perform()
        else:  # Windows
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
            actions.perform()
        
        time.sleep(0.5)

    def get_neighbor_blogs(self, page: int = 1) -> List[Tuple[str, str]]:
        """이웃새글 목록을 가져옵니다."""
        try:
            print(f"6. 네이버 블로그 홈페이지로 이동 (페이지 {page})...")
            # 네이버 블로그 홈페이지로 직접 이동 (페이지 번호 포함)
            self.driver.get(f"https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage={page}&groupId=0")
            time.sleep(5)  # 페이지 로딩 대기
            
            print("7. 이웃새글 목록 로드 대기...")
            # 이웃새글 목록이 로드될 때까지 대기
            wait = WebDriverWait(self.driver, 15)
            
            # 이웃새글 섹션을 먼저 찾고, 그 안에서 게시물을 선택
            buddy_section = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'section.wrap_thumbnail_post_list'))
            )
            
            # 페이지 끝까지 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 이웃새글 섹션 내의 게시물만 선택
            posts = buddy_section.find_elements(By.CSS_SELECTOR, 'div.item.multi_pic')
            
            print(f"8. 찾은 이웃 게시물 수: {len(posts)}")
            
            blog_links = []
            seen_urls = set()
            
            print("9. 게시물 정보 추출 시작...")
            # 게시물 정보 추출
            for i, post in enumerate(posts, 1):
                try:
                    print(f"\n게시물 {i} 처리 중...")
                    
                    # 게시물 링크에서 blogId와 logNo 추출
                    post_link = post.find_element(By.CSS_SELECTOR, 'a.desc_inner')
                    href = post_link.get_attribute('href')
                    print(f"링크: {href}")
                    
                    if not href or href in seen_urls:
                        print("이미 처리된 링크이거나 유효하지 않은 링크입니다.")
                        continue
                    
                    blog_id_match = re.search(r'blog\.naver\.com/([^/]+)', href)
                    post_id_match = re.search(r'/(\d+)(?:\?|$)', href)
                    
                    if blog_id_match and post_id_match:
                        blog_id = blog_id_match.group(1)
                        post_id = post_id_match.group(1)
                        print(f"블로그 ID: {blog_id}, 포스트 ID: {post_id}")
                        
                        blog_links.append((blog_id, post_id))
                        seen_urls.add(href)
                        print(f"게시물 {i} 처리 완료")
                        
                except Exception as e:
                    print(f"게시물 {i} 처리 중 오류 발생: {str(e)}")
                    continue
            
            # 최대 10개로 제한
            result_links = blog_links[:10]
            
            print(f"\n이웃새글 {len(result_links)}개를 찾았습니다.")
            
            return result_links
            
        except Exception as e:
            print(f"이웃새글 목록을 가져오는 중 오류 발생: {str(e)}")
            print(f"상세 오류: {e.__class__.__name__}")
            return []

def run():
    """프로그램 실행"""
    try:
        # 봇 인스턴스 생성
        bot = NaverBot()
        bot.process_pages()
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")
        if bot.driver:
            bot.driver.quit()

if __name__ == "__main__":
    run() 