try:
	from paddleocr import PaddleOCR
	_paddleocr_import_error = None
except Exception as _err:  # pragma: no cover - runtime environment dependent
	PaddleOCR = None
	_paddleocr_import_error = _err

from PIL import Image


def ocr_with_paddle(image_path, lang: str = 'en', use_angle_cls: bool = True, font_path: str | None = None):
	"""Perform OCR on `image_path` using PaddleOCR and return (visualized_image, data).

	- visualized_image: a PIL Image with drawn OCR results
	- data: list of tuples (box, text, score)

	Raises ImportError with actionable install instructions if `paddleocr` is not available.
	"""
	if _paddleocr_import_error is not None:
		raise ImportError(
			"Missing dependency 'paddleocr'. Install it with:\n"
			"    python -m pip install paddleocr\n\n"
			"On Windows you may also need a compatible `paddlepaddle` wheel. See: https://www.paddlepaddle.org.cn/install/quick"
		) from _paddleocr_import_error

	ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
	results = ocr.ocr(image_path)

	# Extract bounding boxes, texts, and confidence scores
	boxes = [line[0] for line in results[0]]
	texts = [line[1][0] for line in results[0]]
	scores = [line[1][1] for line in results[0]]

	# Load the image using PIL
	image = Image.open(image_path).convert('RGB')

	# Draw OCR results on the image using a small PIL fallback
	def draw_ocr_fallback(pil_image, boxes, texts, scores, font_path=None):
		from PIL import ImageDraw, ImageFont

		draw = ImageDraw.Draw(pil_image)
		try:
			font = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
		except Exception:
			font = ImageFont.load_default()

		for box, text, score in zip(boxes, texts, scores):
			# box is list of 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
			try:
				coords = [(int(x), int(y)) for x, y in box]
			except Exception:
				# fallback if box is already flattened
				coords = []
			if coords:
				draw.line(coords + [coords[0]], width=2, fill=(255, 0, 0))
				# place text at top-left
				draw.text((coords[0][0], coords[0][1] - 12), f"{text} ({score:.2f})", fill=(0, 255, 0), font=font)

		return pil_image

	visualized_image = draw_ocr_fallback(image, boxes, texts, scores, font_path=font_path)

	data = list(zip(boxes, texts, scores))
	return visualized_image, data


if __name__ == '__main__':
	import sys

	if len(sys.argv) < 2:
		print('Usage: python models/OCR.py <image_path>')
		sys.exit(1)

	image_path = sys.argv[1]
	try:
		visualized_image, data = ocr_with_paddle(image_path)
		out = 'output_image.jpg'
		visualized_image.save(out)
		print(f'Saved OCR visualization to {out}')
	except ImportError as ie:
		print(ie)
		sys.exit(2)
	except Exception as e:
		print(f'OCR failed: {e}')
		sys.exit(3)
