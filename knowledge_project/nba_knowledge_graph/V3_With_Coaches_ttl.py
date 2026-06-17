from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster
from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL
import time

# 1. Ayarlar
g = Graph()
# En son oluşturduğumuz V2 dosyasını baz alıyoruz
input_file = "NBA_Ontology_Final_V2.ttl"
g.parse(input_file, format="turtle")

NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# 2. Tüm Takımları Döngüye Al
all_teams = teams.get_teams()
print(f"{len(all_teams)} takım için koç verileri çekiliyor...")

for team in all_teams:
    team_name = team['full_name'].replace(" ", "_")
    team_id = team['id']
    
    try:
        # Takım kadrosunu ve koçlarını çek
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        # Coaches tablosu genellikle 1. indekstedir
        coaches_df = roster.get_data_frames()[1] 
        
        # Sadece baş antrenörü (Head Coach) alalım
        head_coach = coaches_df[coaches_df['COACH_TYPE'].str.contains("Head Coach", na=False)]
        
        if not head_coach.empty:
            coach_name = head_coach.iloc[0]['COACH_NAME']
            coach_uri = NBA[coach_name.replace(" ", "_")]
            team_uri = NBA[team_name]
            
            # Bireyi Sınıfına Ata
            g.add((coach_uri, RDF.type, OWL.NamedIndividual))
            g.add((coach_uri, RDF.type, NBA.Coach))
            
            # İlişkiyi Kur (Coach -> coaches -> Team)
            g.add((coach_uri, NBA.coaches, team_uri))
            
            # İsmini veri olarak ekle
            g.add((coach_uri, NBA.playerName, Literal(coach_name))) # playerName mülkünü label niyetine kullanıyoruz
            
            print(f"  [EKLENDİ] {coach_name} -> {team['full_name']}")
            
        time.sleep(0.5) # API koruması
        
    except Exception as e:
        print(f"  [HATA] {team['full_name']} koç verisi alınamadı: {e}")

# 3. Kaydet
output_file = "NBA_Ontology_Final_V3_With_Coaches.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"\nİşlem tamam! Koçlar eklendi: {output_file}")