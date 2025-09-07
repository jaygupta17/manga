import asyncio
import img2pdf
from PIL import Image
from gemini import client
from pydantic import BaseModel
from io import BytesIO
import os

async def upload_and_wait_for_file(file:str):
  try:
    file = await client.aio.files.upload(file=file)
    while file.state!="ACTIVE":
      if file.state=="FAILED":
        raise Exception(f"File {file.name} failed to upload")
      await asyncio.sleep(0.4)
    return file
  except Exception as e:
    print(e)
    raise e

async def structured(prompt:str, schema:BaseModel | list[BaseModel],model:str='gemini-2.5-pro',files:list[str]=[]):
  try:
    files = [await upload_and_wait_for_file(file) for file in files if os.path.exists(file)] if files else []
    response = client.models.generate_content(
      model=model,
      contents=[*files,prompt] if files else [prompt],
      config={
          "response_mime_type": "application/json",
          "response_schema": schema,
          "max_output_tokens": 60000
      },
    )
    return response.parsed
  except Exception as e:
    print(e)
    raise e

async def generate_image(prompt:str,path:str,images:list[str]) -> str:
  try:
    contents = [prompt]
    for img in images:
      if os.path.exists(img):
        contents.insert(0,Image.open(img))
    print(contents)
    response = client.models.generate_content(
      model="gemini-2.5-flash-image-preview",
      contents=contents
    )
    for part in response.candidates[0].content.parts:
      if part.text is not None:
          print(part.text)
      elif part.inline_data is not None:
          image = Image.open(BytesIO(part.inline_data.data))
          image.save(path)
    return path
  except Exception as e:
    print(e)
    raise e

async def get_pdf(image_paths:list[str],pdf_path:str):
    try:
        pdf_bytes = img2pdf.convert(image_paths)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Successfully converted {image_paths} to {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"An error occurred: {e}")

async def clean_string(string:str):
  return string.replace("/", "_")