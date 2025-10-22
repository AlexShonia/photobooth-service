from io import BytesIO
import sys
from PIL import Image, ImageWin

if sys.platform == "win32":
    import win32print
    import win32ui


def print_image(image_bytes, doc_name="Image Print"):
    try:
        if sys.platform != "win32":
            print(f"🖨️ Skipping print (not on Windows)")
            return

        img = Image.open(BytesIO(image_bytes)).convert("RGB")

        printer_name = win32print.GetDefaultPrinter()
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)

        paper_width = hDC.GetDeviceCaps(110)  # PHYSICALWIDTH
        paper_height = hDC.GetDeviceCaps(111)  # PHYSICALHEIGHT

        dpi_x = hDC.GetDeviceCaps(88)  # LOGPIXELSX
        dpi_y = hDC.GetDeviceCaps(90)  # LOGPIXELSY
        width_inches = paper_width / dpi_x
        height_inches = paper_height / dpi_y

        print(
            f'🖨️ Paper size: {width_inches:.1f}" x {height_inches:.1f}" '
            f"({paper_width}x{paper_height} pixels)"
        )

        # Resize to fit paper
        img = img.resize((paper_width, paper_height), Image.LANCZOS)

        # Start print job
        hDC.StartDoc(doc_name)
        hDC.StartPage()

        dib = ImageWin.Dib(img)
        dib.draw(hDC.GetHandleOutput(), (0, 0, paper_width, paper_height))

        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        print("✅ Printed successfully.")

    except Exception as e:
        print("❌ Failed to print:", e)
