from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster
from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL, XSD
import time

# ==========================================
# 1. AYARLAR VE YÜKLEME
# ==========================================
g = Graph()
input_file = "NBA_Ontology_Final_V3_With_Coaches.ttl" # Bir önceki dosyamız
g.parse(input_file, format="turtle")

NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# ==========================================
# 2. KONFERANS EKSİKLİĞİNİ GİDERME
# ==========================================
print("1. Konferanslar ve Takım Atamaları Yapılıyor...")

# Konferans Bireylerini Oluştur
east_conf = NBA["Eastern_Conference"]
west_conf = NBA["Western_Conference"]

g.add((east_conf, RDF.type, OWL.NamedIndividual))
g.add((east_conf, RDF.type, NBA.EasternConferance)) # Ontolojindeki yazıma göre
g.add((west_conf, RDF.type, OWL.NamedIndividual))
g.add((west_conf, RDF.type, NBA.WesternConferance))

# Doğu ve Batı Takımları Listesi (Kesin Veri)
eastern_teams = ["Atlanta_Hawks", "Boston_Celtics", "Brooklyn_Nets", "Charlotte_Hornets", "Chicago_Bulls", "Cleveland_Cavaliers", "Detroit_Pistons", "Indiana_Pacers", "Miami_Heat", "Milwaukee_Bucks", "New_York_Knicks", "Orlando_Magic", "Philadelphia_76ers", "Toronto_Raptors", "Washington_Wizards"]

all_teams = teams.get_teams()
for team in all_teams:
    team_name = team['full_name'].replace(" ", "_")
    team_uri = NBA[team_name]
    
    # Takım ontolojide varsa Konferansa bağla
    if (team_uri, RDF.type, NBA.Team) in g:
        if team_name in eastern_teams:
            g.add((team_uri, NBA.belongsTo, east_conf))
        else:
            g.add((team_uri, NBA.belongsTo, west_conf))

# ==========================================
# 3. FORMA NUMARASI VE POZİSYON EKSİKLİĞİNİ GİDERME
# ==========================================
print("\n2. Oyuncu Pozisyonları ve Forma Numaraları Ekleniyor...")

for team in all_teams:
    team_id = team['id']
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        df = roster.get_data_frames()[0] # Oyuncular tablosu
        
        for index, row in df.iterrows():
            player_name = row['PLAYER'].replace(" ", "_")
            player_uri = NBA[player_name]
            
            # Eğer bu oyuncu LLM tarafından ontolojiye daha önce eklendiyse (yani yaşıyorsa)
            if (player_uri, RDF.type, NBA.Player) in g:
                
                # Forma Numarası (hasJerseyNumber) Ekle
                jersey = str(row['NUM']).strip()
                if jersey.isdigit(): # Sadece rakamsa al
                    g.add((player_uri, NBA.hasJerseyNumber, Literal(int(jersey), datatype=XSD.int)))
                
                # Pozisyon (playPosition) Ekle
                pos_raw = str(row['POSITION']).upper()
                if "G" in pos_raw:
                    g.add((player_uri, NBA.playPosition, NBA.Guard))
                elif "F" in pos_raw:
                    g.add((player_uri, NBA.playPosition, NBA.Forward))
                elif "C" in pos_raw:
                    g.add((player_uri, NBA.playPosition, NBA.Center))
                    
        time.sleep(0.5) # API limit koruması
    except Exception as e:
        print(f"[HATA] {team['full_name']} verisi çekilemedi: {e}")

# ==========================================
# 4. KAYDETME
# ==========================================
output_file = "NBA_Ontology_Final_V4_Complete.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"\nMÜKEMMEL! Tüm eksikler giderildi. Yeni dosya: {output_file}")