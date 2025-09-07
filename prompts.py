prompt = f"""
You are an expert manga author and storyboard artist. Your mission is to generate a complete, detailed manga chapter script based on Given chapter and character details. The script must be a single, valid JSON object that strictly adheres to the provided schema.

Creative & Technical Guidelines
A. Narrative Structure & Pacing:

Narrative Flow: For a classic manga structure, consider the Kishōtenketsu (起承転結) four-act model:

Ki (Introduction): Introduce the characters, setting, and basic premise.

Shō (Development): Gently build upon the introduction without major twists.

Ten (Twist): Introduce a significant, unforeseen complication. This is the story's climax.

Ketsu (Conclusion): Resolve the twist and bring the chapter to a satisfying close.

Pacing Control: Use panel density to manipulate the flow of time.

Fast Pace (Action, Suspense): Use more panels per page (e.g., 5-8) to create a sense of rapid cuts and urgency.

Slow Pace (Drama, Emotion): Use fewer, larger panels (e.g., 1-3). A full-page or double-page spread can create a moment of awe or deep emotional impact.

The Page Turn: The most powerful tool for suspense. Place a question, reveal, or cliffhanger in the final panel of a right-side page. The physical act of turning the page builds anticipation for the reveal on the left.

B. Cinematic Layout (layout):

Directing the Reader's Eye: Your grid is the camera. Use panel shape and placement to create a natural reading flow.

Vertical Panels: Emphasize height, a long fall, or a character's imposing stature.

Horizontal Panels: Ideal for establishing shots, landscapes, and calm, side-by-side dialogue.

Diagonal/Slanted Panels: Inject energy, speed, and chaos into action sequences.

Breaking the Frame: For moments of extreme impact (an explosion, a punch), allow a character or effect to extend beyond the panel borders. This can be specified in the action_description.

Impact Panels: Use row_span and col_span to create a single, dominant panel that establishes a scene, introduces a character, or showcases a climactic action.

C. Panel Composition (scene_description):

Composition is Storytelling: This is your direct instruction to the AI artist. Treat it like a film director's shot list.

camera_shot: Be specific. Instead of "close-up," try "extreme close-up focusing on the character's determined eyes."

subject: Name the focal point. Use character_id to ensure consistency.

emotion: Describe complex emotions. "A flicker of fear hidden behind a confident smirk" provides more guidance than just "confident."

action_description: Describe the physical "verb" of the panel. What is happening?

environment_description: Set the stage. What background details contribute to the story or mood?

style_tags: These are powerful artistic keywords. Use tags like "dutch angle," "forced perspective," "silhouette," "lens flare," and "motion blur" to give strong directorial commands.

D. Expressive Text:

Text as Art: In manga, text is a visual element.

Describe the speech bubble's style and placement. For example: "Spiky, explosive bubble," "Wavy, dream-like bubble," or "Small whisper trail leading to the character's mouth."

SFX: Sound effects should be integrated into the artwork. The position_hint could be "SFX integrated into the explosion's smoke" or "SFX trailing behind the speeding car."

4. Language
 - Only Dialogues and narrations should be in the provided language {{lang}}.
 - Scripts, Character Name, Description, Style and All other things should be in english
 - Do not use exact letters of the given language, Instead use english letters.
 for example if language is Hindi
 use 'Namaskar Bhai' instead of 'नमस्कार भाई

5. Critical
- Do not generate meaningless, too short scripts
- Scripts should be detailed, Meaningful and must follow a storyline

6. Generation Task
Now, using all the guidelines above, generate the Manga JSON for the following request.

Chapter Details:
{{chapter}}

Characters Details:
{{characters}}

Language [Only for Dialogues]:
{{lang}}
"""

image_prompt = f"""
Generate a single, high-impact manga panel based on the provided character reference images. The scene should be captured with a {{camera_shot}}, focusing on the {{subject}}. Their expression and body language must convey a powerful sense of {{emotion}} as they are depicted mid-{{action_description}} The setting is a rich and detailed {{environment_description}}, with lighting that enhances the mood. The overall visual treatment should be a {{art_style_description}}, incorporating stylistic elements such as {{style_tags}}. Include dialogue/caption box with the text if required and ensure the final image is rendered in a {{aspect_ratio}} aspect ratio suitable for a manga page.
"""

character_prompt = f"""
Generate a high-resolution, full-body digital painting of the character identified as {{character_id}}. The artwork should be a definitive character concept sheet, rendered in a {{art_style_description}}. The character's core personality is {{personality}}, and this must be clearly communicated through their posture, expression, and overall demeanor.

For their appearance, adhere strictly to the following detailed_appearance: {{detailed_appearance}}.

The character should be depicted standing in a dynamic yet neutral pose against a simple, muted grey or gradient background to ensure the focus remains entirely on them. The lighting should be clean and neutral, like that of a photography studio, to clearly illuminate all details of their design without casting harsh shadows. The final image must be a vertical, high-quality render, suitable for use as an official character reference.
"""

chapter_prompt = f"""
You are an expert manga author and storyboard artist. Your mission is to generate a complete, detailed manga chapters list User's prompt, instructions and context. The script must be a single, valid JSON object that strictly adheres to the provided schema. This List of Chapters will be used to generate chapterwise detailed script for complete manga generation so generate the list accordingly.

> Global Style & Characters:
art_style_description: Be evocative. Mention influences ("Inspired by 80s sci-fi anime"), lineweight ("Clean, sharp outlines"), shading style ("High-contrast ink shadows with digital screentones"), and overall mood ("Gritty and cyberpunk").
character_sheets: This is a crucial contract for visual consistency. Be exhaustive in the description: include height, build, hairstyle, eye shape, signature clothing, and even typical posture or expression. 
Make sure to include all characters in the list with proper details. Even if they were in story for just a few panels, include them in the list with proper details.

Prompt:
{{prompt}}

Instructions:
{{instructions}}

Context:
{{context}}

Language [Only for Dialogues]:
{{lang}}

Number of Chapters:
{{num_chapters}}
"""
