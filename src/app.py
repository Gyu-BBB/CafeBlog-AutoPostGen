# src/app.py
import os
import re
import json
import urllib.request
import urllib.parse
import openai
import streamlit as st
from PIL import Image
from io import BytesIO
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from transformers import BlipProcessor, BlipForConditionalGeneration

# def get_api_keys():
#     # secrets.toml 파일에서 정보 가져오기
#     st.write("Checking secrets...")
#     st.write("OPENAI_API_KEY:", st.secrets.get("OPENAI_API_KEY"))
#     st.write("NAVER_CLIENT_ID:", st.secrets.get("NAVER_CLIENT_ID"))
#     st.write("NAVER_CLIENT_SECRET:", st.secrets.get("NAVER_CLIENT_SECRET"))
    
#     # 기존 코드
#     api_key = st.secrets.get("OPENAI_API_KEY")
#     client_id = st.secrets.get("NAVER_CLIENT_ID")
#     client_secret = st.secrets.get("NAVER_CLIENT_SECRET")
    
#     if not api_key or not client_id or not client_secret:
#         st.error("OPENAI_API_KEY, NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")
#         st.stop()
    
#     return api_key, client_id, client_secret


def get_api_keys():
    # 테스트용으로 API 키를 직접 설정
    api_key = ""
    client_id = ""
    client_secret = ""

    if not api_key or not client_id or not client_secret:
        st.error("OPENAI_API_KEY, NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")
        st.stop()
    
    return api_key, client_id, client_secret

def create_openai_client(api_key):
    # OpenAI API 키 설정
    openai.api_key = api_key
    return openai  # openai 모듈 자체를 반환


def analyze_uploaded_images(uploaded_images):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    
    captions = []
    image_filenames = []
    
    for uploaded_file in uploaded_images:
        image = Image.open(uploaded_file)
        inputs = processor(images=image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        captions.append(f"{caption} {{{uploaded_file.name}}}")
        image_filenames.append(uploaded_file.name)
        st.write(f"파일: {uploaded_file.name}, 생성된 캡션: {caption}")
    
    return captions

def read_sys_prompt(prompt_name):
    # 기본 프롬프트 설정
    prompts = {
        "first_sys_prompt": {
            "content": "당신은 키워드 추출 전문가입니다. 사용자의 질문에서 핵심 키워드를 추출하세요."
        },
        "second_sys_prompt": {
            "content": "당신은 글 작성 전문가입니다. 아래의 정보를 바탕으로 게시글을 작성하세요."
        },
        "third_sys_prompt": {
            "formats": {
                "naver_blog": "네이버 블로그 형식으로 작성해주세요."
            }
        }
    }
    return prompts.get(prompt_name, {"content": ""})

def generate_keywords(client, first_sys_prompt_content, user_question):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": first_sys_prompt_content
            },
            {
                "role": "user",
                "content": user_question
            }
        ]
    )

    keyword = completion.choices[0].message.content.strip()
    print(f"추출된 키워드: {keyword}")
    return keyword

def search_naver_blog(client_id, client_secret, keyword):
    encText = urllib.parse.quote(keyword)
    display = 5
    start = 1
    sort = "sim"
    
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={display}&start={start}&sort={sort}"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        response_body = response.read()
        result = json.loads(response_body.decode('utf-8'))

        if "items" in result and len(result["items"]) > 0:
            description_all = ' '.join([item["description"] for item in result["items"]])
            clean_description = re.sub(r'<\/?b>', '', description_all)
            st.write(f"참고자료: {clean_description}")
        else:
            clean_description = "참고 자료가 없습니다."
    except Exception as e:
        st.error("블로그 검색 중 오류가 발생했습니다.")
        st.error(str(e))
        clean_description = "참고 자료가 없습니다."
    return clean_description

def choose_tone(tone_choice):
    # 톤 선택 사전
    tones = {
        "1": "formal",      # 공식적/비즈니스 어조
        "2": "casual",      # 친근하고 가벼운 어조
        "3": "humorous",    # 유머러스한 어조
        "4": "informative"  # 정보 제공형 어조
    }
    # 선택한 톤 반환, 기본은 'casual'
    return tones.get(str(tone_choice), "casual")

def generate_final_post(client, second_sys_prompt_content, third_sys_prompt_content, user_question, clean_description, image_captions, example_text, tone=None):
    # 톤 프롬프트에 추가 (tone이 있으면 해당하는 프롬프트 추가)
    tone_instruction = f"Please write in a {tone} tone." if tone else ""
    example_text_content = f"Here is an example of the user's previous writing style: {example_text}" if example_text else "The user has not provided an example text."

    final_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"{second_sys_prompt_content}\n\n{tone_instruction}\n\n글 형식:{third_sys_prompt_content}"
            },
            {
                "role": "user",
                "content": f"사용자의 질문: {user_question}\n참고자료: {clean_description}\n입력된 사진: {' '.join(image_captions)}\n글 형식: {example_text_content}"
            }
        ]
    )

    final_post = final_completion.choices[0].message.content.strip()
    return final_post

def apply_md_formatting(paragraph, text):
    # 인라인 마크다운 서식을 적용합니다.
    # 패턴 정의
    pattern = r'(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*|`.+?`|~~.+?~~|__.+?__|!.+?\(.*?\)|\[.+?\]\(.*?\))'
    tokens = re.split(pattern, text)

    for token in tokens:
        if not token:
            continue
        if token.startswith('***') and token.endswith('***'):
            # 굵게 및 기울임
            run = paragraph.add_run(token[3:-3])
            run.bold = True
            run.italic = True
        elif token.startswith('**') and token.endswith('**'):
            # 굵게
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith('*') and token.endswith('*'):
            # 기울임
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        elif token.startswith('~~') and token.endswith('~~'):
            # 취소선
            run = paragraph.add_run(token[2:-2])
            run.font.strike = True
        elif token.startswith('`') and token.endswith('`'):
            # 인라인 코드
            run = paragraph.add_run(token[1:-1])
            run.font.name = 'Courier New'
            run.font.size = Pt(10)
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            # 하이퍼링크
            link_text = token[1:token.index(']')]
            link_url = token[token.index('](')+2:-1]
            run = paragraph.add_run(f'{link_text} ({link_url})')
            run.font.color.rgb = RGBColor(0, 0, 255)  # 파란색으로 표시
            run.font.underline = True
        else:
            # 일반 텍스트
            run = paragraph.add_run(token)

def save_post_to_word(final_post, uploaded_images):
    doc = Document()
    image_files = {img.name: img for img in uploaded_images}

    for line in final_post.split('\n'):
        # {} 또는 () 형식의 이미지 태그 인식
        image_match = re.search(r'[\{\(](.+?\.(?:jpg|jpeg|png))[\}\)]', line)

        if image_match:
            # 이미지 파일 이름 추출
            image_name = image_match.group(1)
            # 업로드된 이미지 파일 찾기
            image_file = image_files.get(image_name)
            if image_file:
                # 이미지 삽입
                doc.add_picture(image_file, width=Inches(5))
            else:
                # 이미지가 없으면 오류 메시지 추가
                line_text = re.sub(r'[\{\(].+?\.(?:jpg|jpeg|png)[\}\)]', f"[이미지 '{image_name}'를 찾을 수 없습니다]", line)
                paragraph = doc.add_paragraph()
                apply_md_formatting(paragraph, line_text)
        else:
            # 이미지 태그가 없는 경우 텍스트에 서식 적용
            paragraph = doc.add_paragraph()
            apply_md_formatting(paragraph, line)

    # BytesIO를 사용하여 메모리에 저장
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def main():
    st.set_page_config(page_title="자동 게시글 생성 시스템", layout="wide")
    st.title("📄 이미지 및 텍스트 분석을 통한 자동 게시글 생성 시스템")

    # API 키 가져오기
    api_key, client_id, client_secret = get_api_keys()
    client = create_openai_client(api_key)  # OpenAI 클라이언트를 생성하고 저장

    # 사이드바 입력
    st.sidebar.header("📝 입력 설정")
    user_question = st.sidebar.text_area("작성하고자 하는 내용 입력", "")

    # 톤 선택
    tone_options = {
        "1": "formal",      # 공식적/비즈니스 어조
        "2": "casual",      # 친근하고 가벼운 어조
        "3": "humorous",    # 유머러스한 어조
        "4": "informative"  # 정보 제공형 어조
    }
    tone_choice = st.sidebar.selectbox("톤 선택", options=list(tone_options.keys()), format_func=lambda x: tone_options[x])
    tone = tone_options[tone_choice]

    # 이미지 업로드
    uploaded_images = st.sidebar.file_uploader("이미지 업로드", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

    # 예시 텍스트 입력
    example_text = st.sidebar.text_area("예시 텍스트 입력 (선택사항)", "")

    if st.sidebar.button("게시글 생성"):
        if not user_question:
            st.error("작성하고자 하는 내용을 입력하세요.")
            return

        # 이미지 캡션 생성
        if uploaded_images:
            with st.spinner("이미지 분석 중..."):
                image_captions = analyze_uploaded_images(uploaded_images)
        else:
            image_captions = []

        # 시스템 프롬프트 읽기
        first_sys_prompt = read_sys_prompt('first_sys_prompt')
        second_sys_prompt = read_sys_prompt('second_sys_prompt')
        third_sys_prompt = read_sys_prompt('third_sys_prompt')

        # 키워드 생성
        with st.spinner("키워드 생성 중..."):
            keyword = generate_keywords(client, first_sys_prompt["content"], user_question)  # client 인자 추가
            st.write(f"### 추출된 키워드: {keyword}")

        # 네이버 블로그 검색
        with st.spinner("블로그 검색 중..."):
            clean_description = search_naver_blog(client_id, client_secret, keyword)
            st.write(f"### 참고자료:\n{clean_description}")

        # 게시글 생성
        chosen_format = third_sys_prompt["formats"]["naver_blog"]
        with st.spinner("게시글 생성 중..."):
            final_post = generate_final_post(client, second_sys_prompt["content"], chosen_format, user_question, clean_description, image_captions, example_text, tone)

        st.write("## 생성된 게시글")
        st.write(final_post)

        # 게시글 Word 파일로 저장
        word_file = save_post_to_word(final_post, uploaded_images)
        st.download_button(
            label="📥 게시글 Word 파일로 다운로드",
            data=word_file,
            file_name="generated_post_with_images.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if __name__ == "__main__":
    main()
