import os
from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HF_TOKEN")
client = InferenceClient(token=HF_TOKEN)

def extract_nba_triples(text):
    # Source 3'e tam uyumlu Few-Shot Prompting
    messages = [
        {
            "role": "system", 
            "content": "You are a Knowledge Graph extraction bot. You only output triples in the exact format requested. Do not include any conversational filler."
        },
        {
            "role": "user", 
            "content": f"""
            Target Schema:
            - playsFor(Player, Team)
            - hasHeight(Player, Decimal)
            - playsPosition(Player, Position)

            Example Input: "LeBron James is a forward for the Lakers standing 2.06m."
            Example Output:
            LeBron_James | playsPosition | Forward_Pos
            LeBron_James | playsFor | LA_Lakers
            LeBron_James | hasHeight | 2.06

            Task: Extract triples from this text.
            Text: "{text}"
            Output:
            """
        }
    ]
    
    try:
        # Llama-3'ün en optimize versiyonu
        response = client.chat_completion(
            messages=messages,
            model="meta-llama/Meta-Llama-3-8B-Instruct", 
            max_tokens=200,
            temperature=0.1 # Halüsinasyonu sıfıra indirmek için
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Hata detayı: {str(e)}"

# Test
print("Llama-3 Yanıtı Bekleniyor...\n")
sonuc = extract_nba_triples("Stephen Curry plays for the Golden State Warriors and is 1.88 meters tall.")
print(sonuc)