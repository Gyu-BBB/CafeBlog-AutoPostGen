import os
import openai
import urllib.request
import urllib.parse
import json

# OpenAI 설정
openai.api_key = ""
openai.api_base = ""

# Naver API 설정
client_id = ""
client_secret = ""

def get_keywords_from_input(user_input):
    response = openai.ChatCompletion.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": "Extract the most relevant keywords in a form that is appropriate for searching. Only provide keywords without full sentences or unnecessary words."},
            {"role": "user", "content": user_input}
        ]
    )
    keywords = response.choices[0].message['content']
    keywords_clean = keywords.strip().replace('\n', ' ').replace(',', ' ')
    return keywords_clean

def search_naver_blog(keywords):
    encText = urllib.parse.quote(keywords)
    url = "https://openapi.naver.com/v1/search/blog?query=" + encText  # JSON 결과
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    
    if rescode == 200:
        response_body = response.read()
        result = response_body.decode('utf-8')
        return result
    else:
        print("Error Code:" + str(rescode))
        return None

def save_to_txt(search_result):
    # 검색 결과를 파싱하여 텍스트로 변환
    search_data = json.loads(search_result)
    items = search_data.get('items', [])
    
    # 현재 실행 중인 스크립트와 동일한 폴더 경로 가져오기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # TXT 파일에 검색 결과 저장
    txt_output_path = os.path.join(current_dir, "naver_blog_search_results.txt")
    
    with open(txt_output_path, 'w', encoding='utf-8') as file:
        file.write("네이버 블로그 검색 결과 요약\n\n")
        for item in items:
            title = item['title'].replace("<b>", "").replace("</b>", "")
            description = item['description'].replace("<b>", "").replace("</b>", "")
            link = item['link']
            file.write(f"제목: {title}\n")
            file.write(f"설명: {description}\n")
            file.write(f"링크: {link}\n\n")
    
    return txt_output_path

# 사용자 입력
user_input = "요즘 유행하는 프로그래밍 언어"

# 1. 사용자 입력에서 키워드 추출
keywords = get_keywords_from_input(user_input)
print(f"추출된 키워드: {keywords}")

# 2. 추출된 키워드로 네이버 블로그 검색
search_result = search_naver_blog(keywords)

# 3. 검색 결과를 TXT 파일로 저장
if search_result:
    txt_file_path = save_to_txt(search_result)
    print(f"검색 결과가 TXT 파일로 저장되었습니다: {txt_file_path}")
else:
    print("검색 결과를 가져오지 못했습니다.")
