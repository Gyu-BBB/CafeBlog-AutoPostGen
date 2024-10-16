from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

# 이미지 로드
url = "./data/example.jpg"  # 로컬 파일 사용
image = Image.open(url)

# BLIP 모델 로드 (한국어 지원 모델 사용)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# 이미지 전처리
inputs = processor(images=image, return_tensors="pt")

# 이미지 캡션 생성
out = model.generate(**inputs, max_new_tokens=50)
caption = processor.decode(out[0], skip_special_tokens=True)

# 결과 출력
print(f"생성된 캡션: {caption}")