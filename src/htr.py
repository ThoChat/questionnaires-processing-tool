from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

# choose a small handwritten model; first run downloads it, then it’s cached locally
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def recognize_handwriting(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        generated_ids = model.generate(pixel_values, max_length=64)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()

if __name__ == "__main__":
    print(recognize_handwriting("/home/marvin/Dokumente/Temp/pedestriancrowds/sample_handwritten_single_line.png"))