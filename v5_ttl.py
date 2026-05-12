import time
import re
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster
from rdflib import Graph, URIRef, Literal, Namespace, RDF, XSD

# 1. Yükleme
g = Graph()
input_file = "NBA_Ontology_Final_V4_Complete.ttl" # Son oluşturduğun dosya
g.parse(input_file, format="turtle")

NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# Boy Dönüştürücü (6-3 gibi API formatlarını Metreye çevirir)
def clean_and_convert_height(raw_height):
    try:
        numbers = re.findall(r'\d+', str(raw_height))
        if len(numbers) >= 2:
            feet = int(numbers[0])
            inches = int(numbers[1])
            total_inches = (feet * 12) + inches
            return round(total_inches * 0.0254, 2)
        return None
    except:
        return None

print("Boy verileri NBA API'den çekilip metreye çevriliyor...")

# 2. API'den Veri Çekme ve Ekleme
all_teams = teams.get_teams()
for team in all_teams:
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team['id'])
        df = roster.get_data_frames()[0]
        
        for index, row in df.iterrows():
            player_name = row['PLAYER'].replace(" ", "_")
            player_uri = NBA[player_name]
            
            # Eğer oyuncu ontolojide varsa boyunu ekle
            if (player_uri, RDF.type, NBA.Player) in g:
                h_meters = clean_and_convert_height(row['HEIGHT'])
                
                if h_meters:
                    # Data Property olarak ekliyoruz
                    g.add((player_uri, NBA.hasHeight, Literal(h_meters, datatype=XSD.double)))
                    
        time.sleep(0.5) # API koruması
    except Exception as e:
        print(f"Hata ({team['full_name']}): {e}")

# 3. Kaydetme
output_file = "NBA_Ontology_Final_V5.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"\nHarika! Boy verileri eklendi ve {output_file} kaydedildi.")