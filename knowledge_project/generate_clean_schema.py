from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL, RDFS, XSD

g = Graph()
NBA = Namespace("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.bind("nba", NBA)

# --- METADATA (Widoco'nun çökmesini engelleyen zorunlu alanlar) ---
ontology_uri = URIRef("http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/")
g.add((ontology_uri, RDF.type, OWL.Ontology))
g.add((ontology_uri, RDFS.label, Literal("NBA Knowledge Graph Ontology", lang="en")))
g.add((ontology_uri, RDFS.comment, Literal("An integrated ontology for NBA players, coaches, teams, conferences, and arenas.", lang="en")))

# --- CLASSES (Sınıflar) ---
classes = ["Player", "Coach", "Team", "Arena", "Conference", "Guard", "Forward", "Center", "EasternConferance", "WesternConferance"]
for cls in classes:
    g.add((NBA[cls], RDF.type, OWL.Class))
    g.add((NBA[cls], RDFS.label, Literal(cls, lang="en")))

# Subclass Relationships
g.add((NBA["Guard"], RDFS.subClassOf, NBA["Player"]))
g.add((NBA["Forward"], RDFS.subClassOf, NBA["Player"]))
g.add((NBA["Center"], RDFS.subClassOf, NBA["Player"]))
g.add((NBA["EasternConferance"], RDFS.subClassOf, NBA["Conference"]))
g.add((NBA["WesternConferance"], RDFS.subClassOf, NBA["Conference"]))

# --- OBJECT PROPERTIES (Nesne Mülkleri) ---
obj_props = {
    "playsFor": ("Player", "Team"),
    "playPosition": ("Player", "Class"),
    "coaches": ("Coach", "Team"),
    "belongsTo": ("Team", "Conference"),
    "hasHomeArena": ("Team", "Arena")
}
for prop, (domain, range_cls) in obj_props.items():
    g.add((NBA[prop], RDF.type, OWL.ObjectProperty))
    g.add((NBA[prop], RDFS.label, Literal(prop, lang="en")))
    g.add((NBA[prop], RDFS.domain, NBA[domain]))
    if range_cls != "Class":
        g.add((NBA[prop], RDFS.range, NBA[range_cls]))

# --- DATA PROPERTIES (Veri Mülkleri) ---
data_props = {
    "hasHeight": ("Player", XSD.double),
    "hasJerseyNumber": ("Player", XSD.int),
    "playerName": ("OWL.Thing", XSD.string),
    "hasCapacity": ("Arena", XSD.int)
}
for prop, (domain, datatype) in data_props.items():
    g.add((NBA[prop], RDF.type, OWL.DatatypeProperty))
    g.add((NBA[prop], RDFS.label, Literal(prop, lang="en")))
    if domain != "OWL.Thing":
        g.add((NBA[prop], RDFS.domain, NBA[domain]))
    g.add((NBA[prop], RDFS.range, datatype))

# Dosyayı kaydet
g.serialize(destination="NBA_Pure_Schema.ttl", format="turtle")
print("[SUCCESS] Widoco için tamamen temizlenmiş saf şema dosyası oluşturuldu: NBA_Pure_Schema.ttl")