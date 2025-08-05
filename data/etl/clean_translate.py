import pandas as pd
# from transformers import MarianMTModel, MarianTokenizer
import re
import json

def load_data(file_path):
    df = pd.read_csv(file_path)
    df = df[['Query Text', 'Kcc ']]  # Adjust column names
    df.dropna(inplace=True)
    return df

# Example: Load MarianMT for Hindi → English
def load_translator():
    model_name = "Helsinki-NLP/opus-mt-hi-en"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model

def translate(texts, tokenizer, model):
    batch = tokenizer.prepare_seq2seq_batch(texts, return_tensors="pt", padding=True)
    translated = model.generate(**batch)
    return [tokenizer.decode(t, skip_special_tokens=True) for t in translated]

def clean_text(text):
    return re.sub(r"[^A-Za-z0-9\s.,?!]", "", str(text)).strip()

def run_clean_and_translate(input_csv, output_json):
    df = load_data(input_csv)
    tokenizer, model = load_translator()

    clean_data = []
    for i, row in df.iterrows():
        q = clean_text(row['Farmer_Question'])
        a = clean_text(row['Answer'])

        # Translate if detected to be Hindi (simple heuristic)
        if re.search(r'[\u0900-\u097F]', q):  # Devanagari script
            q = translate([q], tokenizer, model)[0]
        if re.search(r'[\u0900-\u097F]', a):
            a = translate([a], tokenizer, model)[0]

        clean_data.append({"question": q, "answer": a})

    with open(output_json, "w") as f:
        json.dump(clean_data, f, indent=2)

if __name__ == "__main__":
    run_clean_and_translate(
        input_csv="../raw/kcc_transcripts.csv",
        output_json="../processed/clean_translated.json"
    )
