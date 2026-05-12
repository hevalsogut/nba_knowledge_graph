import os
import time
import re
from huggingface_hub import InferenceClient
from rdflib import Graph, URIRef, Literal, Namespace, RDF, XSD
from rdflib.namespace import OWL

# ==========================================
# 1. SETTINGS & CONFIGURATION
# ==========================================
HF_TOKEN = "***REMOVED***" # Enter your Hugging Face token here
client = InferenceClient(token=HF_TOKEN)

# Namespace URI MUST exactly match your Protégé ontology
NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

EXISTING_TTL = "Knowledge_Project_Skeleton.ttl" 
FINAL_TTL = "NBA_Ontology_Full_Final.ttl"
INPUT_DIR = "nba_unstructured_data"

# Whitelist for allowed predicates (Prevents LLM Hallucination)
ALLOWED_PREDS = ["playsFor", "hasHeight", "playsPosition"]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_and_convert_height(raw_height):
    """ Converts various height formats (e.g., 6-3, 6'11") into meters. """
    try:
        # If it's already in decimal format (e.g., 2.11)
        if '.' in raw_height:
            return float(re.search(r'\d+\.\d+', raw_height).group())
            
        # Extract numbers for feet and inches
        numbers = re.findall(r'\d+', raw_height)
        if len(numbers) >= 2:
            feet = int(numbers[0])
            inches = int(numbers[1])
            total_inches = (feet * 12) + inches
            return round(total_inches * 0.0254, 2)
        return None
    except:
        return None

def extract_triples_safe(player_name, bio_text):
    """ Uses LLaMA-3 to extract triples strictly conforming to the ontology schema. """
    messages = [
        {
            "role": "system",
            "content": """You are a strict data extraction bot for an NBA Ontology. 
CRITICAL RULES:
1. ONLY use these EXACT three predicates: playsFor, hasHeight, playsPosition. Do NOT invent new ones like 'wasTradedTo' or 'isBrotherOf'.
2. For 'playsFor', ONLY extract current or former professional NBA teams. DO NOT extract high school or college/university teams (e.g., UCLA Bruins, Arizona Wildcats).
3. If a value is unknown, output NULL.
4. Output ONLY the triples.
5. If the team is not a professional NBA team (e.g., NFL, NHL or Soccer teams), do NOT extract it."
EXAMPLE:
Text: Aaron Gordon played for the Arizona Wildcats before joining the Orlando Magic. He is 6-8.
Output:
Aaron_Gordon | playsFor | Orlando_Magic
Aaron_Gordon | hasHeight | 6-8"""
        },
        {
            "role": "user",
            "content": f"Text: {bio_text[:1200]}\nOutput:"
        }
    ]
    
    try:
        response = client.chat_completion(
            messages=messages,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            max_tokens=100,
            temperature=0.01
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"API_ERROR|{str(e)}"

# ==========================================
# 3. ONTOLOGY PROCESSING (MAIN PIPELINE)
# ==========================================
g = Graph()
g.bind("nba", NBA)

# Attempt to load the skeleton ontology
if os.path.exists(EXISTING_TTL):
    try:
        g.parse(EXISTING_TTL, format="turtle")
        print(f"[SUCCESS] Skeleton file loaded: {EXISTING_TTL}. Current triples: {len(g)}")
    except Exception as e:
        print(f"[WARNING] Could not read the skeleton file! Error: {e}")
else:
    print(f"[WARNING] Skeleton file '{EXISTING_TTL}' not found. Starting with an empty graph.")

# Process the text files
if not os.path.exists(INPUT_DIR):
    print(f"[ERROR] Directory '{INPUT_DIR}' not found. Please ensure the unstructured data exists.")
else:
    print("\n--- INITIATING FULL DATA EXTRACTION PIPELINE ---")
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    
    # Iterate through ALL files in the directory (No slicing limits)
    for filename in files:
        p_name = filename.replace(".txt", "") # Lock the subject to the exact filename
        file_path = os.path.join(INPUT_DIR, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        print(f"\n=> Processing: {p_name}...")
        result = extract_triples_safe(p_name, content)
        
        # Parse the LLM output
        lines = result.split('\n')
        for line in lines:
            if "|" in line and "API_ERROR" not in line:
                parts = [x.strip() for x in line.split('|')]
                if len(parts) == 3:
                    _, p, o = parts # Ignore the LLM's subject and use our fixed p_name
                    
                    # LAYER 1: Skip null or unknown objects
                    if o.upper() == "NULL" or o == "" or "unknown" in o.lower():
                        continue
                    
                    # LAYER 2: Allow only whitelisted predicates
                    if p not in ALLOWED_PREDS:
                        continue
                        
                    # Fix the Subject URI
                    subj = NBA[p_name]
                    pred = NBA[p]
                    
                    # Type Assertions (Ensure they are classified correctly)
                    g.add((subj, RDF.type, OWL.NamedIndividual))
                    g.add((subj, RDF.type, NBA.Player))
                    
                    # Data vs. Object Property Handling
                    if p == "hasHeight":
                        m_height = clean_and_convert_height(o)
                        if m_height:
                            g.add((subj, pred, Literal(m_height, datatype=XSD.double)))
                            print(f"   [ADDED] Height: {m_height}m")
                    else:
                        obj = NBA[o.replace(" ", "_")]
                        g.add((subj, pred, obj))
                        print(f"   [ADDED] {p}: {o}")
        
        # Rate Limiting: Sleep to avoid Hugging Face API limits
        time.sleep(1.5)

# ==========================================
# 4. FINAL SAVE EXECUTIONS
# ==========================================
print("\n--- PIPELINE EXECUTION SUMMARY ---")
if len(g) > 0:
    g.serialize(destination=FINAL_TTL, format="turtle")
    print(f"[EXCELLENT] Pipeline finished successfully! Total triples saved: {len(g)}")
    print(f"[FILE SAVED] -> {FINAL_TTL}")
else:
    print("[ERROR] Graph is empty. No data was extracted or saved.")