
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD



# 1. Boş bir grafik (Graph) oluştur ve Ontoloji Namespace'ini tanımla
g = Graph()
# Kendi ontolojinin başındaki URI'yi buraya yazmalısın (Aşağıdaki bir örnektir)
nba = Namespace("http://www.semanticweb.org/nba-ontology#")
g.bind("nba", nba)

# LLM'den aldığımız saf çıktı (Döngü ile tüm textleri buraya besleyebilirsin)
llm_output = """
Stephen_Curry | playsFor | Golden_State_Warriors
Stephen_Curry | hasHeight | 1.88
Stephen_Curry | playsPosition |  (Note: Position is not specified in the text, so it is left blank)
"""

# 2. LLM çıktısını ayrıştır (Parsing)
print("RDF Üçlüleri Oluşturuluyor...")
for line in llm_output.strip().split('\n'):
    # Satırı '|' işaretine göre böl ve sağdaki/soldaki boşlukları temizle
    parts = [p.strip() for p in line.split('|')]
    
    # Geçerli bir üçlü ise ve içinde "Note:" (LLM notu) yoksa ontolojiye ekle
    if len(parts) == 3 and "Note:" not in parts[2] and parts[2] != "":
        
        subject_uri = nba[parts[0]] # Örn: nba:Stephen_Curry
        predicate_uri = nba[parts[1]] # Örn: nba:playsFor
        
        # Veri Tipi Kontrolü (Data Property vs Object Property)
        if parts[1] == "hasHeight":
            # Boy sayısal bir değerdir (Literal)
            object_node = Literal(float(parts[2]), datatype=XSD.float)
        else:
            # Diğerleri (Takım, Pozisyon vb.) birer bireydir (URIRef)
            object_node = nba[parts[2]]
            
        # Üçlüyü grafiğe ekle
        g.add((subject_uri, predicate_uri, object_node))
        print(f"Eklendi: {parts[0]} -> {parts[1]} -> {parts[2]}")

# 3. Dosyayı Turtle formatında kaydet
output_file = "nba_populated_data.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"\nİşlem Tamam! Bireyler {output_file} dosyasına kaydedildi.")