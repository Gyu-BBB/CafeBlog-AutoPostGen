from transformers import BlipProcessor, Blip2ForConditionalGeneration
from PIL import Image
import torch

# 이미지 로드
url = "./data/example.jpg"  # 로컬 파일 사용
image = Image.open(url)

# BLIP-2 모델 로드
processor = BlipProcessor.from_pretrained("Salesforce/blip2-flan-t5-xl")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-flan-t5-xl")

# 이미지 전처리
inputs = processor(images=image, return_tensors="pt")

# 이미지 캡션 생성
out = model.generate(**inputs, max_new_tokens=50)
caption = processor.decode(out[0], skip_special_tokens=True)

# 결과 출력
print(f"생성된 캡션: {caption}")
