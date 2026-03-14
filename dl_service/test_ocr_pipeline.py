import sys
import os
import cv2
import json

sys.path.append(os.path.join(os.getcwd(), 'dl_service'))

from services.invoice_service import process_invoice_image

# use one of the test images
test_img_path = "./backup/dl imgs/generated_invoices/test/invoice_test_1080.png"

def run_test():
    print(f"Loading image from {test_img_path}")
    image = cv2.imread(test_img_path)
    if image is None:
        print(f"Failed to load image: {test_img_path}")
        return

    print("Running process_invoice_image...")
    try:
        result = process_invoice_image(image)
        # Drop heavy history for print
        if 'layout_regions' in result:
            result['layout_regions'] = list(result['layout_regions'].keys())
        print("\n--- Final Pipeline Result ---")
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        import traceback
        print("\nError during pipeline execution:")
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
