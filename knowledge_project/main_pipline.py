import os
import time
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster
from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL, XSD

# ==========================================
# 1. SETTINGS & CONFIGURATION
# ==========================================
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(token=HF_TOKEN)

NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

# We start from your healthy 9.24 KB skeleton file
BASE_SKELETON = "Knowledge_Project_Skeleton.ttl"
FINAL_OUTPUT = "NBA_Knowledge_Graph_Complete.ttl"
INPUT_DIR = "nba_unstructured_data"

ALLOWED_PREDS = ["playsFor", "hasHeight", "playPosition"]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def normalize_position(raw):
    """
    Maps free-text LLM position output (e.g. 'Small Forward/Shooting Guard',
    'center', 'Guard/Forward') to exactly one of the ontology's three valid
    Position individuals: Guard, Forward, Center. Takes the first recognized
    position word in reading order (Wikipedia bio convention lists the
    primary position first in combo descriptions). Returns None if nothing
    recognizable is found, so callers can skip the triple instead of
    creating an invalid out-of-vocabulary URI.
    """
    tokens = re.split(r"[\s/\-_,&]+", raw.lower())
    for token in tokens:
        if "guard" in token:
            return "Guard"
        if "forward" in token:
            return "Forward"
        if "center" in token:
            return "Center"
    return None


def convert_height(raw):
    try:
        nums = re.findall(r'\d+', str(raw))
        if len(nums) >= 2:
            total_inches = (int(nums[0]) * 12) + int(nums[1])
            return round(total_inches * 0.0254, 2)
        return None
    except: 
        return None

def llm_extract_safe(p_name, text):
    system_prompt = f"""You are a strict data extraction bot for an NBA Ontology.
CRITICAL RULES:
1. ONLY use these EXACT three predicates: playsFor, hasHeight, playPosition.
2. ONLY extract professional NBA teams. Do NOT extract college/university or high school teams.
3. If a value is unknown, output NULL.
4. OUTPUT ONLY THE TRIPLES using format: Subject | Predicate | Object
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Text: {text[:1200]}\nOutput:"}
    ]
    try:
        resp = client.chat_completion(messages=messages, model="meta-llama/Meta-Llama-3-8B-Instruct", max_tokens=100, temperature=0.01)
        return resp.choices[0].message.content.strip()
    except Exception as e: 
        return f"API_ERROR|{e}"

# ==========================================
# 3. PIPELINE EXECUTION
# ==========================================
g = Graph()
g.bind("nba", NBA)

print("--- Step 1: Loading Healthy Skeleton Base ---")
if os.path.exists(BASE_SKELETON):
    g.parse(BASE_SKELETON, format="turtle")
    print(f"[SUCCESS] Loaded baseline skeleton with {len(g)} triples.")
else:
    print("[ERROR] Knowledge_Project_Skeleton.ttl not found! Please check your directory.")
    exit()

print("\n--- Step 2: Safe LLM Extraction from Unstructured Data ---")
if os.path.exists(INPUT_DIR):
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    total_files = len(files)
    
    for idx, filename in enumerate(files):
        p_name = filename.replace(".txt", "")
        print(f"[{idx+1}/{total_files}] Extracting text data for: {p_name}...")
        
        with open(os.path.join(INPUT_DIR, filename), "r", encoding="utf-8") as f:
            raw_result = llm_extract_safe(p_name, f.read())
        
        for line in raw_result.split('\n'):
            if "|" in line and "API_ERROR" not in line:
                parts = [x.strip() for x in line.split('|')]
                # VALUE ERROR PROTECTION: Ensure exactly 3 parts exist
                if len(parts) == 3:
                    _, p, o = parts
                    if p in ALLOWED_PREDS and o.upper() != "NULL" and o != "":
                        subj = NBA[p_name]
                        g.add((subj, RDF.type, OWL.NamedIndividual))
                        g.add((subj, RDF.type, NBA.Player))
                        if p != "hasHeight":
                            obj_local = o.replace(" ", "_")
                            if p == "playPosition":
                                normalized = normalize_position(o)
                                if normalized is None:
                                    continue  # unrecognized position text, skip rather than create garbage URI
                                obj_local = normalized
                            # playsFor / playPosition are single-valued (see shapes.ttl
                            # maxCount 1) -- remove any prior value from this same bio
                            # extraction before adding the new one, instead of
                            # accumulating duplicates (e.g. the 3x playPosition seen
                            # on Chet_Holmgren / Jaylen_Brown).
                            g.remove((subj, NBA[p], None))
                            g.add((subj, NBA[p], NBA[obj_local]))
        time.sleep(1.2)

print("\n--- Step 3: API Enrichment (Coaches, Conferences, Precise Stats) ---")
east_conf = NBA["Eastern_Conference"]
west_conf = NBA["Western_Conference"]
g.add((east_conf, RDF.type, NBA.EasternConference))
g.add((west_conf, RDF.type, NBA.WesternConference))

eastern_teams = ["Atlanta_Hawks", "Boston_Celtics", "Brooklyn_Nets", "Charlotte_Hornets", "Chicago_Bulls", 
                 "Cleveland_Cavaliers", "Detroit_Pistons", "Indiana_Pacers", "Miami_Heat", "Milwaukee_Bucks", 
                 "New_York_Knicks", "Orlando_Magic", "Philadelphia_76ers", "Toronto_Raptors", "Washington_Wizards"]

all_teams = teams.get_teams()
for t in all_teams:
    t_id = t['id']
    t_name = t['full_name'].replace(" ", "_")
    t_uri = NBA[t_name]
    
    if t_name in eastern_teams:
        g.add((t_uri, NBA.belongsTo, east_conf))
    else:
        g.add((t_uri, NBA.belongsTo, west_conf))
        
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=t_id)
        
        # 3.1 Coaches
        c_df = roster.get_data_frames()[1]
        hc = c_df[c_df['COACH_TYPE'].str.contains("Head Coach", na=False)]
        if not hc.empty:
            c_name = hc.iloc[0]['COACH_NAME']
            c_uri = NBA[c_name.replace(" ", "_")]
            g.add((c_uri, RDF.type, OWL.NamedIndividual))
            g.add((c_uri, RDF.type, NBA.Coach))
            g.add((c_uri, NBA.coaches, t_uri))
            g.add((c_uri, NBA.playerName, Literal(c_name, datatype=XSD.string)))

        # 3.2 Numerical Overwrites
        p_df = roster.get_data_frames()[0]
        for _, row in p_df.iterrows():
            p_uri = NBA[row['PLAYER'].replace(" ", "_")]
            if (p_uri, RDF.type, NBA.Player) in g:
                g.add((p_uri, NBA.hasJerseyNumber, Literal(int(row['NUM']), datatype=XSD.int)))
                h_met = convert_height(row['HEIGHT'])
                if h_met:
                    g.remove((p_uri, NBA.hasHeight, None))
                    g.add((p_uri, NBA.hasHeight, Literal(h_met, datatype=XSD.double)))
        time.sleep(0.5)
    except Exception as e: 
        print(f"Skipping API enrichment for {t['full_name']} due to timeout/error.")

# ==========================================
# 4. SAVE FINAL QUALITY BASE
# ==========================================
g.serialize(destination=FINAL_OUTPUT, format="turtle")
print(f"\n[SUCCESS] Unified Graph saved without syntax formatting errors: {FINAL_OUTPUT}")
print(f"Total Triples Created: {len(g)}")