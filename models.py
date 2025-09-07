from pydantic import BaseModel
from enum import Enum

# class TextElementType(str, Enum):
#     DIALOGUE = "dialogue"
#     NARRATION = "narration"
#     SFX = "sfx"

class CharacterSheet(BaseModel):
    character_id: str
    personality: str
    detailed_appearence: str

class GlobalStyle(BaseModel):
    art_style_description: str
    character_sheets: list[CharacterSheet]

class PromptComponents(BaseModel):
    camera_shot: str
    subject: str
    emotion: str
    action_description: str
    environment_description: str
    style_tags: list[str]
    aspect_ratio: str
    character_ids: list[str]

class Panel(BaseModel):
    panel_number: int
    scene_description: PromptComponents

class PanelPlacement(BaseModel):
    panel_number: int
    grid_row: int
    grid_col: int
    row_span: int
    col_span: int

class PageLayout(BaseModel):
    grid_rows: int
    grid_columns: int
    placements: list[PanelPlacement]

class Page(BaseModel):
    page_number: int
    layout: PageLayout
    panels: list[Panel]

class MangaChapterScript(BaseModel):
    chapter_number: int
    chapter_title: str
    pages: list[Page]

class Chapter(BaseModel):
    chapter_number: int
    chapter_title: str
    story: str

class Manga(BaseModel):
  title: str
  global_style: GlobalStyle
  chapters: list[Chapter]

class MainRequest(BaseModel):
  prompt: str
  context: str
  instructions: str
  num_chapters: int = 5
  lang:str = 'english'
  model: str = 'gemini-2.5-pro'

class MangaRequest(BaseModel):
  prompt: str
  context: str
  instructions: str
  num_chapters: int = 5
  lang:str = 'english'
  model: str = 'gemini-2.5-pro'

class ChapterRequest(BaseModel):
  chapter: Chapter
  global_style: GlobalStyle
  lang:str = 'english'
  model: str = 'gemini-2.5-pro'

class CharacterRequest(BaseModel):
  manga: str
  global_style: GlobalStyle

class PanelRequest(BaseModel):
  manga: str
  scene_description: PromptComponents
  global_style: GlobalStyle
  id: str
  model: str = 'gemini-2.5-pro'
