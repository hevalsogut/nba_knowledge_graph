from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL, RDFS, XSD

# 1. Grafiği Oluştur ve Mevcut Dosyayı Yükle
g = Graph()
# Eğer dosyan aynı klasördeyse yükle, yoksa sıfırdan başla
try:
    g.parse("Knowledge_Proeject.ttl", format="turtle")
    print("Mevcut ontoloji başarıyla yüklendi.")
except:
    print("Dosya bulunamadı, yeni bir grafik oluşturuluyor.")

# 2. Namespace Tanımlama (Dosyandaki URI ile birebir aynı olmalı)
NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# 3. YENİ SINIFLARIN TANIMLANMASI (Phase 2 Genişletmesi)
new_classes = ["Award", "Season", "Draft"]
for cls in new_classes:
    g.add((NBA[cls], RDF.type, OWL.Class))
    g.add((NBA[cls], RDFS.subClassOf, NBA["NBA-Member"]))

# 4. YENİ DATA PROPERTY TANIMLAMA
g.add((NBA.hasSalary, RDF.type, OWL.DatatypeProperty))
g.add((NBA.hasSalary, RDFS.domain, NBA.Player))
g.add((NBA.hasSalary, RDFS.range, XSD.integer))

# 5. LLM'DEN GELEN VERİLERİ VE LİSTEYİ EKLEME (Individiuals)
# Önceki aşamada hazırladığın listeden örnekler
players_data = [
    {"id": "Gary_Payton_II", "team": "GoldenState", "height": 1.88, "pos": "Guard"},
    {"id": "Brandin_Podziemski", "team": "GoldenState", "height": 1.93, "pos": "Guard"},
    {"id": "Kristaps_Porzingis", "team": "BostonCeltics", "height": 2.18, "pos": "Center"}
]

print("Bireyler ve ilişkiler ekleniyor...")
for data in players_data:
    p_uri = NBA[data["id"]]
    
    # Bireyi Sınıfına Ata
    g.add((p_uri, RDF.type, OWL.NamedIndividual))
    g.add((p_uri, RDF.type, NBA.Player))
    
    # Veri Mülklerini Ekle (Data Properties)
    g.add((p_uri, NBA.hasHeight, Literal(data["height"], datatype=XSD.double)))
    g.add((p_uri, NBA.playerName, Literal(data["id"].replace("_", " "), datatype=XSD.string)))
    
    # Nesne Mülklerini Ekle (Object Properties)
    g.add((p_uri, NBA.playsFor, NBA[data["team"]]))
    
    # Pozisyon Sınıfına Göre Ata
    if data["pos"] == "Guard":
        g.add((p_uri, RDF.type, NBA.Guard))
    elif data["pos"] == "Center":
        g.add((p_uri, RDF.type, NBA.Center))

# 6. SONUÇLARI KAYDET
output_file = "Knowledge_Project_V2.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"\nİşlem tamamlandı! '{output_file}' dosyası oluşturuldu.")