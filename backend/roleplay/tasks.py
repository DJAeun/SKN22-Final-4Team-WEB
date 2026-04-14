from celery import shared_task
from django.conf import settings
from .models import RpgSession, RpgChatLog, RpgHyperMemory, RpgMessageEmbedding
from kss import split_sentences
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import re
import json


IMAGE_COMMAND_PATTERN = re.compile(r'<img="([a-z0-9_]+)">', re.IGNORECASE)


def get_memory_safe_content(text: str) -> str:
    cleaned = IMAGE_COMMAND_PATTERN.sub('', text or '')
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

@shared_task
def run_embedding_task(chat_log_id: int):
    log = RpgChatLog.objects.get(id=chat_log_id)
    # Using kss to split Korean sentences cleanly
    sentences = split_sentences(get_memory_safe_content(log.content))
    
    # Initialize embeddings model
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    for chunk in sentences:
        if chunk.strip():
            vector = embeddings.embed_query(chunk)
            RpgMessageEmbedding.objects.create(
                session=log.session,
                chat_log=log,
                chunk_content=chunk,
                embedding=vector
            )

@shared_task
def run_hypermemory_task(session_id: str):
    session = RpgSession.objects.get(id=session_id)
    
    prompts_dir = settings.BASE_DIR / 'roleplay' / 'prompts'
    rule_file = prompts_dir / 'hypermemoryprompt.md'
    prompt_sys = rule_file.read_text(encoding='utf-8')
    
    last_memory = RpgHyperMemory.objects.filter(session=session).order_by('-created_at').first()
    last_msg_id = last_memory.last_msg.id if last_memory and last_memory.last_msg else 0
    
    logs_to_summarize = RpgChatLog.objects.filter(session=session, id__gt=last_msg_id).order_by('id')
    if not logs_to_summarize.exists():
        return
        
    relay_novel = "\n".join([f"{l.role}: {get_memory_safe_content(l.content)}" for l in logs_to_summarize])
    
    # Inject exactly where {{slot}} is
    prompt = prompt_sys.replace('{{slot}}', relay_novel)
    
    from google import genai
    from google.genai import types
    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(category="HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            ],
            temperature=1.0,
        )
    )
    raw_text = response.text
    
    # Check for <Compressed> block
    match = re.search(r'<Compressed characters="(.*?)">(.*?)<\/Compressed>', raw_text, re.DOTALL)
    if not match:
        return
    
    characters_present = [c.strip() for c in match.group(1).split(',')]
    content = match.group(2).strip()
    
    # Parse the sections
    parsed_data = parse_hypermemory_sections(content)
    
    # Reset token counts for summarized logs assuming we do it here, or just let session handle it
    
    # Create new HyperMemory
    RpgHyperMemory.objects.create(
        session=session,
        # In a real setup, in-game dates/times should be scraped from parsed_data['Time and Place']
        location_transition=parsed_data.get('Time and Place', ''),
        characters_present=characters_present,
        context_overview=parsed_data.get('Context Overview', ''),
        events=parsed_data.get('Events', '').split('\n- '),
        infos=parsed_data.get('Infos', '').split('\n- '),
        emotional_dynamics=parsed_data.get('Emotional Dynamics', ''),
        dialogues=parsed_data.get('Dialogues', '').split('\n- '),
        last_msg=logs_to_summarize.last()
    )
    
def parse_hypermemory_sections(content: str) -> dict:
    """Helper purely to parse the dash-separated text output into logical blocks."""
    sections = {}
    current_key = None
    current_val = []
    
    # Simple parsing heuristic
    for line in content.split('\n'):
        if line.startswith('- Time and Place:'):
            sections['Time and Place'] = line.replace('- Time and Place:', '').strip()
        elif line.startswith('- Context Overview:'):
            sections['Context Overview'] = line.replace('- Context Overview:', '').strip()
        elif line.startswith('- Events:'):
            current_key = 'Events'
        elif line.startswith('- Infos:'):
            current_key = 'Infos'
        elif line.startswith('- Emotional Dynamics:'):
            sections['Emotional Dynamics'] = line.replace('- Emotional Dynamics:', '').strip()
        elif line.startswith('- Dialogues:'):
            current_key = 'Dialogues'
        else:
            if current_key and line.strip():
                current_val.append(line.strip())
                sections[current_key] = '\n'.join(current_val)
                
    return sections
