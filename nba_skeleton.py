from nba_api.stats.static import teams
from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL

# 1. Ayarlar
g = Graph()
g.parse("Knowledge_Proeject.ttl", format="turtle")
NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# 2. Tüm NBA Takımlarını Çek
all_teams = teams.get_teams()

print("Takımlar ve Arenalar iskelete ekleniyor...")
for team in all_teams:
    team_uri = NBA[team['full_name'].replace(" ", "_")]
    # Bu bireyin bir 'Team' olduğunu tanımla
    g.add((team_uri, RDF.type, OWL.NamedIndividual))
    g.add((team_uri, RDF.type, NBA.Team))
    
    # Takım ismini veri olarak ekle
    g.add((team_uri, NBA.playerName, Literal(team['full_name']))) # playerName mülkünü genel kullandığını varsayıyorum

    # Arenaları ekleyelim (Eğer verin varsa)
    # nba_api her zaman arena vermez, bu yüzden örnek bir eşleme:
    arena_uri = NBA[f"{team['full_name'].replace(' ', '_')}_Arena"]
    g.add((arena_uri, RDF.type, NBA.Arena))
    g.add((team_uri, NBA.hasHomeArena, arena_uri))

# 3. Kaydet
g.serialize(destination="Knowledge_Project_Skeleton.ttl", format="turtle")
