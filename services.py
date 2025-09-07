from models import Manga, MangaRequest, ChapterRequest, CharacterRequest, PanelRequest, MangaChapterScript
from prompts import chapter_prompt, character_prompt, prompt, image_prompt
from utils import clean_string, structured, generate_image
from pathlib import Path
DATA_DIR = Path("nanobanana_data")

async def generate_chapters(req: MangaRequest) -> Manga:
  formatted_prompt = chapter_prompt.format(**req.model_dump())
  result: Manga = await structured(formatted_prompt,Manga,req.model)
  return result

async def generate_characters(req: CharacterRequest):
  for character in req.global_style.character_sheets:
      cprompt = character_prompt.format(**{
          'character_id': character.character_id,
          'personality': character.personality,
          'detailed_appearance': character.detailed_appearence,
          'art_style_description': req.global_style.art_style_description
      })
      path = f'{DATA_DIR}/{await clean_string(req.manga)}/{await clean_string(character.character_id)}.png'
      path = await generate_image(cprompt,path,[])

async def process_chapter(req: ChapterRequest) -> MangaChapterScript:
  try:
    characters = '\n****\n'.join([
        f'{ch.character_id}\nPersonality:\n{ch.personality}\nAppearance:\n{ch.detailed_appearence}' 
        for ch in req.global_style.character_sheets
        ])
    chapter = f"""
    {req.chapter.chapter_title}
    {req.chapter.story}
    """
    formatted_prompt = prompt.format(**{
        'chapter': chapter,
        'characters': characters,
        'lang': req.lang
    })
    result: MangaChapterScript = await structured(formatted_prompt,MangaChapterScript,req.model)
    return result
  except Exception as e:
    print(e)

async def process_panel(req: PanelRequest) -> str:
  iprompt = image_prompt.format(**{
                'camera_shot': req.scene_description.camera_shot,
                'subject': req.scene_description.subject,
                'emotion': req.scene_description.emotion,
                'action_description': req.scene_description.action_description,
                'environment_description': req.scene_description.environment_description,
                'art_style_description': req.global_style.art_style_description,
                'style_tags': ','.join(req.scene_description.style_tags),
                'aspect_ratio': req.scene_description.aspect_ratio
  })
  path = f'{DATA_DIR}/{await clean_string(req.manga)}/{await clean_string(req.id)}.png'
  images = [f'{DATA_DIR}/{await clean_string(req.manga)}/{await clean_string(ch)}.png' for ch in req.scene_description.character_ids]
  imgpath = await generate_image(iprompt,path,images)
  return imgpath
