import streamlit as st
from rembg import remove
from PIL import Image
from io import BytesIO
import base64

st.set_page_config(layout="wide", page_title="Voronoi. Label Studio")

st.write("## Clinical dataset labelling...")

st.sidebar.write("## Upload and download :gear:")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def convert_image(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    return byte_im


def fix_image(upload):
    image = Image.open(upload)
    col1.write("Paper PDF Image")
    col1.image(image)

    fixed = remove(image)
    col2.write("Suggested Table :wrench:")
    col2.image(fixed)
    st.sidebar.markdown("\n")
    st.sidebar.download_button("Download fixed image", convert_image(fixed), "fixed.png", "image/png")


col1, col2 = st.columns(2)
paper_pdf_upload = st.sidebar.file_uploader("Paper PDF format", type=["PDF"])

if paper_pdf_upload is not None:
    if paper_pdf_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        fix_image(upload=paper_pdf_upload) ## 여기서 호출해야함.
else:
    fix_image("./zebra.jpg")