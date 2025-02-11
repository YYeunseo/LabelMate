## update 2025-02-11
## 

import streamlit as st
from rembg import remove
from PIL import Image
from io import BytesIO
import base64
import os
import json
from openai import OpenAI
import pandas as pd
from io import StringIO
import pdfplumber
from langchain.document_loaders import PyMuPDFLoader
import base64
import fitz



st.set_page_config(layout="wide", page_title="Voronoi. Label Studio")

st.write("## Clinical dataset LabelMate")
st.markdown("Please upload your files (the **full paper** and **table images**) first, and review the table generated by GPT. There may be **errors**, so please check carefully.")
left, middle, right = st.columns(3)
st.sidebar.write("## Upload and download :gear:")

# MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

col1, col2 = st.columns(2)
paper_pdf_upload = st.sidebar.file_uploader("Full Paper PDF format", type=["PDF"], ) # 1개까지 허용
paper_efficacy_upload = st.sidebar.file_uploader("Efficacy Table PNG format", type=["PNG"]) # 3개까지 허용
paper_toxicity_upload = st.sidebar.file_uploader("Toxicity Table PNG format", type=["PNG"]) # 3개까지 허용
paper_dose_upload = st.sidebar.file_uploader("Dose info Table PNG format", type=["PNG"]) # 3개까지 허용

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def pdf_to_text(upload):

    #################################### related text data 뽑기 ####################################

    print("EFFICACY Table Generating...")
    print("\n\n[[[논문에서 초록과 EFFICACY 본문]]]\n")

    if upload is not None:
            # `upload`는 UploadedFile 객체이므로, 파일을 메모리에서 바로 읽어 처리합니다.
            file_bytes = upload.read()
            
            # PyMuPDFLoader가 파일 경로를 기대하므로, BytesIO 객체로 파일을 전달
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
            # 모든 페이지의 텍스트 추출
            full_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                full_text += page.get_text()

            client = OpenAI()
            response_text = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"제공한 텍스트 자료에서 Abstract 문단 내용과 efficacy에 대해 설명하고 있는 모든 문단들을 가져와서 출력해줘. 텍스트 자료:{full_text}.",
                            },
                        ],
                    }
                ],
            )

            related_text_input = response_text.choices[0].message.content
            print("최종 사용할 논문 본문 내용:\n", related_text_input)
            return related_text_input

def efficacy_table_image(upload):
    
    if upload:
        base64_image = encode_image(upload.read())
        client = OpenAI()
        response_replic = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """

                            **해야하는 일 **
                            제공된 이미지에 있는 표를 텍스트 표로 바꿔서 csv format으로 반환해줘.
                            추가 설명은 주지 말고 CSV 포멧 표만 반환해.
                            이때, 표에 함께 있는 caption 글을 csv format 맨 밑에 행에 함께 반환해줘.

                            **고려할 것**
                            행/열을 잘 구분하고, 이때 **띄어쓰기나 볼드체 등의 특징**을 보고, **상위 개념 하위 개념** 관계를 모두 파악하여 상위항목(예를 들어 Objective response rate)-하위항목(at 8 mo)으로 **합쳐서 행**으로 만들어줘.

                            """,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        )

        # print(response_middle.choices[0])
        response_replic = response_replic.choices[0].message.content
        #print('\n\n[STEP 2] 이미지에서 표 복제 text content:\n',response_replic)

        rows111 = response_replic.split("\n")
        data111 = [row.split(",") for row in rows111]
        df111 = pd.DataFrame(data111)
        df111 = df111.applymap(lambda x: x.replace('"', '') if isinstance(x, str) else x)
        #print("\n df111: ",df111)

        related_table_input = df111.to_csv(index=False)
        print("\n df_csv:",related_table_input)
    else:
            related_table_input = None
    return related_table_input

def efficacy_table(related_table_input, related_text_input):
    client = OpenAI()
    response_our_excel = client.chat.completions.create(
      model="gpt-4o",
      messages=[
          {
              "role": "user",
              "content": f"""
              You will be given a CSV table as input. Your task is to transform this table into a new structured format based on the following strict rules:

              ### **Input Data Rules:**
              - The input is:
              ```
              {related_table_input}, {related_text_input}
              ```
              - **Do NOT modify, rephrase, summarize, omit, or alter any text, numbers, units, expressions, or symbols in any way.**
              - **Preserve full content, even if the text is long or contains commas, parentheses, or special characters.**
              - **Extract data exactly as it appears in the original table, maintaining full text integrity.**
              - Extract the correct values **by matching the row and column structure**, ensuring that all content from the relevant cells is fully retained.

              ### **Output Data Structure:**
              The output should be a new table with the following columns:
              ["treat_group", "sub_group", "no. patients", "category", "value(#)","value(%)", "range_type", "range_low", "range_high"]
              Each column follows these strict rules:
              - **treat_group**: 용량 단위로 구분이 되어져있을 경우, 여기다가 용량을 써줘.
              - **sub_group**: Extracted from the column headers of the input table. 용량 정보가 있다면 용량 정보는 빼줘.
              - **no. patients**: The total number of patients in each `sub_group`, extracted exactly as written (수치만 적어야해. 예를 들어, 총 환자 수가 몇 명인지를 N=10 이렇게 표시하지말고, 10이라고 적어.).
              - **category**: Extracted from row headers, containing treatment responses **exactly as written** (e.g., `"Progression-free survival†, Median (95% CI) — mo"`, including all symbols, punctuation, and formatting).
              - **Do NOT cut, truncate, or shorten this text in any way. The full row header must be preserved exactly as in the input.**
              - Check if the value represents a count (#) or a percentage (%), and categorize it accordingly as value (#) or value (%). mo의 경우 #에 적고, 그냥 수치인지 퍼센티지인지 구분해서 맞는 column에 넣어. metric은 적지 않아도 돼.
              - **Do NOT alter or remove units. If the cell contains multiple values, keep them together as a single string.**
              - **range_type**: Extract the confidence interval or range exactly as stated (e.g., `"95% CI"`).
              - **range_low** / **range_high**: Extract the exact minimum and maximum values from the range **without modification**.

              ### **Strict Output Rules:**
              - **Preserve all formatting, symbols, parentheses, spacing, commas, and special characters exactly as they appear in the input.**
              - **If a value includes a comma but was in a single cell in the original table, KEEP IT TOGETHER. Do NOT separate it into multiple columns.**
              - **Ensure that "category" contains the full original row header text without omission. DO NOT truncate long text.**
              - **DO NOT split, modify, or remove any part of the extracted data. Every cell must remain fully intact.**
              - **Return the final structured data in pure CSV format, with no additional text, explanations, or notes.**
              """
          }
      ]
  )

    # prompt에 5-2) 나중에 후처리 때 처리해줘야함. 중간 csv만 빼오기.

    print(response_our_excel)
    response_our_excel_data = response_our_excel.choices[0].message.content

    rows111 = response_our_excel_data.split("\n")
    data111 = [row.split(",") for row in rows111]
    df111 = pd.DataFrame(data111)
    df111 = df111.applymap(lambda x: x.replace('"', '') if isinstance(x, str) else x)

    header_idx = df111[df111[0] == 'treat_group'].index[0]
    df111.columns = df111.iloc[header_idx].values
    df_cleaned = df111.iloc[header_idx + 1:].reset_index(drop=True)
    end_idx = df_cleaned[df_cleaned.iloc[:, 0].str.contains('```', na=False)].index[0]
    efficacy_output = df_cleaned.iloc[:end_idx].reset_index(drop=True)

    efficacy_output = efficacy_output.sort_values(by=['treat_group', 'sub_group'], ascending=[True, True]).reset_index(drop=True)
    return efficacy_output

def get_image_height(upload):
    image = Image.open(upload)
    width, height = image.size  
    return height

def show_original_image(upload):
    image = Image.open(upload)
    width, height = image.size
    col1.write("Original Image :camera:")
    col1.image(image)

def show_generated_table(upload):
    # edited_df = st.data_editor(upload, use_container_width=True)
    image_height = get_image_height(paper_efficacy_upload)
    col2.write("Suggested Table :wrench:")
    col2.data_editor(upload, use_container_width=True, height=image_height)

if left.button("Efficacy Run", use_container_width=True):

    status_placeholder_left = left.empty()
    if paper_pdf_upload is None and paper_efficacy_upload is None:
        status_placeholder_left.markdown("Please upload your files!")

    else:
        status_placeholder_left.markdown("Reading the paper...")
        if paper_pdf_upload is not None:  # 없을 경우, 넣으라고 지시하기. 두 개는 허용 X
            related_text_input = pdf_to_text(upload=paper_pdf_upload)

        status_placeholder_left.markdown("Recognizing the table in the image...")
        if paper_efficacy_upload is not None: # 없을 경우, (하나일 경우), 두개일 경우 처리하기.
            related_table_input = efficacy_table_image(upload=paper_efficacy_upload)
            show_original_image(paper_efficacy_upload)

        status_placeholder_left.markdown("Organizing the table...")
        efficacy_table_output = efficacy_table(related_table_input, related_text_input)
        show_generated_table(efficacy_table_output)

        status_placeholder_left = left.empty()


if middle.button("Toxicity Run", use_container_width=True):
    
    status_placeholder_middle = middle.empty()

    if paper_pdf_upload is None and paper_efficacy_upload is None:
        status_placeholder_middle.markdown("Please upload your files!")

    else:
        status_placeholder_middle.markdown("Reading the paper...")

if right.button("Save", use_container_width=True):
    
    status_placeholder_right = right.empty()