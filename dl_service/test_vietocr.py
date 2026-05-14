import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'dl_service/models/vietocr'))

from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image

try:
    config = Cfg.load_config_from_name('vgg_transformer')
    config['device'] = 'cpu'
    predictor = Predictor(config)
    img = Image.new('RGB', (100, 32), color = (255, 255, 255))
    result = predictor.predict(img)
    print("Success! text:", result)
except Exception as e:
    print("Error:", e)
