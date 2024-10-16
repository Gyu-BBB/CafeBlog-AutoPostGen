import os
import sys
import urllib.request

# 환경 변수에서 client_id와 client_secret 불러오기
client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")

if not client_id or not client_secret:
    print("Client ID 또는 Client Secret이 설정되지 않았습니다.")
    sys.exit()

# 검색어 및 파라미터 설정
encText = urllib.parse.quote("제주도 여행")  # 검색어 인코딩
display = 1  # 표시할 검색 결과 개수 (최대 100)
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
    print(response_body.decode('utf-8'))
else:
    print("Error Code:" + rescode)
