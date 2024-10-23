import os
import sys
import urllib.request
import urllib.parse
import json
import re
import openai
from docx import Document  # Word 문서 생성을 위한 라이브러리
from docx.shared import Inches  # Word에 이미지 크기를 설정하기 위한 라이브러리
from transformers import BlipProcessor, BlipForConditionalGeneration, Blip2ForConditionalGeneration
from PIL import Image
import torch

def get_api_keys():
    # API 키 및 클라이언트 정보 가져오기
    api_key = os.getenv("OPENAI_API_KEY")
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or client_secret is None:
        print("Client ID 또는 Client Secret이 설정되지 않았습니다.")
        sys.exit()
    
    return api_key, client_id, client_secret

def create_openai_client(api_key):
    # OpenAI 클라이언트 생성
    client = openai.OpenAI(api_key=api_key)
    return client

def analyze_images_in_folder():
    # 사진 분석 함수 정의 (호출 시 폴더의 모든 이미지를 읽고 캡션을 생성)
    folder_path = "./data/test/"  # 이미지가 저장된 폴더 경로
    
    # BLIP 모델 로드 (한 번만 로드)
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

    # 결과를 저장할 리스트
    captions = []
    image_filenames = []

    # 폴더 내 파일들에 대해 캡션 생성
    for filename in os.listdir(folder_path):
        # 이미지 파일 필터링 (jpg, jpeg, png 파일만 처리)
        if filename.endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(folder_path, filename)
            
            # 이미지 로드
            image = Image.open(image_path)

            # 이미지 전처리 및 캡션 생성
            inputs = processor(images=image, return_tensors="pt")
            out = model.generate(**inputs, max_new_tokens=50)
            caption = processor.decode(out[0], skip_special_tokens=True)

            # 이미지 파일 이름과 생성된 캡션 저장 (filename: 부분 제거)
            captions.append(f"{caption} {{{filename}}}")
            image_filenames.append(filename)
            print(f"파일: {filename}, 생성된 캡션: {caption}")

    # 이미지 캡션 리스트와 이미지 파일 이름 반환
    return captions, image_filenames

def read_sys_prompt(file_path):
    # 시스템 프롬프트 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as file:
        sys_prompt = json.load(file)
    return sys_prompt

def generate_keywords(client, first_sys_prompt_content, user_question):
    # GPT-4 모델 요청 (첫 번째 프롬프트 사용)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": first_sys_prompt_content  # 첫 번째 시스템 프롬프트
            },
            {
                "role": "user",
                "content": user_question  # 사용자 질문을 변수로 사용
            }
        ]
    )

    # GPT로부터 추출된 키워드
    keyword = completion.choices[0].message.content.strip()
    print(f"추출된 키워드: {keyword}")
    return keyword

def search_naver_blog(client_id, client_secret, keyword):
    # 추출된 키워드를 검색어로 사용
    encText = urllib.parse.quote(keyword)
    display = 10  # 표시할 검색 결과 개수
    start = 1  # 검색 시작 위치
    sort = "sim"  # 정렬 방식 (sim: 정확도순, date: 날짜순)
    
    # URL에 파라미터 추가
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={display}&start={start}&sort={sort}"
    
    # 요청 헤더 설정
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    
    # API 요청 및 응답 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode == 200:
        response_body = response.read()
        result = json.loads(response_body.decode('utf-8'))

        # 'description' 값 추출 및 HTML 태그 제거
        if "items" in result and len(result["items"]) > 0:
            description_all = ' '.join([item["description"] for item in result["items"]])
            clean_description = re.sub(r'<\/?b>', '', description_all)
            print(f"참고자료: {clean_description}")
        else:
            clean_description = "참고 자료가 없습니다."
    else:
        print("Error Code:" + str(rescode))
        clean_description = "참고 자료가 없습니다."
    return clean_description

def generate_final_post(client, second_sys_prompt_content, user_question, clean_description, image_captions):
    # GPT-4 모델 요청 (두 번째 프롬프트 사용)
    final_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": second_sys_prompt_content  # 두 번째 시스템 프롬프트 사용
            },
            {
                "role": "user",
                "content": f"사용자의 질문: {user_question}\n참고자료: {clean_description}\n입력된 사진: {' '.join(image_captions)}\n이 정보를 참고해서 작성해줘."
            }
        ]
    )

    # 최종 생성된 게시글
    final_post = final_completion.choices[0].message.content.strip()
    return final_post

def save_post_to_word(final_post):
    # 서식 문법(###, ** 등) 제거
    clean_final_post = re.sub(r'[#*_]', '', final_post)  # ###, **, * 등 서식 문법 제거
    
    # Word 파일에 저장할 폴더 경로 설정
    output_folder = "./output/"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)  # 폴더가 없으면 생성
    
    # Word 파일에 저장
    doc = Document()  # 새 Word 문서 생성
    
    # 문서에 텍스트를 삽입하면서 이미지 태그를 찾고 해당 위치에 이미지 삽입
    for line in clean_final_post.split('\n'):
        if re.search(r'\{(.*?)\.jpg\}', line):
            # 이미지 태그가 있으면 해당 위치에 이미지 삽입
            image_name = re.search(r'\{(.*?)\}', line).group(1)
            image_path = os.path.join("./data/test/", image_name)
            
            # 이미지 삽입
            if os.path.exists(image_path):
                doc.add_paragraph(line.replace(f'{{image_name}}', ''))
                doc.add_picture(image_path, width=Inches(5))  # 이미지 크기 설정 (5인치 너비)
            else:
                # 이미지가 없으면 텍스트만 추가
                doc.add_paragraph(line.replace(f'{{image_name}}', f"[이미지 '{image_name}'를 찾을 수 없습니다]"))
        else:
            # 이미지 태그가 없으면 그냥 텍스트 삽입
            doc.add_paragraph(line)
    
    # 파일 이름 설정 및 저장
    output_file = os.path.join(output_folder, "generated_post_with_images.docx")
    doc.save(output_file)
    
    print(f"게시글이 {output_file} 파일로 저장되었습니다.")

def main():
    # API 키 및 클라이언트 정보 가져오기
    api_key, client_id, client_secret = get_api_keys()
    
    # OpenAI 클라이언트 생성
    client = create_openai_client(api_key)
    
    # 1st_sys_prompt 파일 읽기
    first_sys_prompt = read_sys_prompt('./data/1st_sys_prompt.json')
    
    # 첫 번째 질문을 변수에 저장
    user_question = "애플 맥북 m2과 m3의 성능비교에 대한 게시글 작성해줘."
    
    # GPT-4 모델 요청 (첫 번째 프롬프트 사용)
    keyword = generate_keywords(client, first_sys_prompt["content"], user_question)
    
    # 추출된 키워드를 검색어로 사용하여 네이버 블로그 검색
    clean_description = search_naver_blog(client_id, client_secret, keyword)
    
    # 2nd_sys_prompt 파일 읽기 (두 번째 GPT 요청을 위한 프롬프트)
    second_sys_prompt = read_sys_prompt('./data/2nd_sys_prompt.json')
    
    # 사진 분석 함수 실행
    image_captions, image_filenames = analyze_images_in_folder()
    
    # GPT-4 모델 요청 (두 번째 프롬프트 사용)
    final_post = generate_final_post(client, second_sys_prompt["content"], user_question, clean_description, image_captions)
    
    # Word 파일로 저장
    save_post_to_word(final_post)

if __name__ == "__main__":
    main()
