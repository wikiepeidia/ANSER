import os, sys
sys.path.append(os.path.join(os.getcwd(), 'dl_service/models/vietocr'))
if True:
    from vietocr.tool.predictor import Predictor
    from vietocr.tool.config import Cfg
print("Ready")
