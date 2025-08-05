from langchain.text_splitter import CharacterTextSplitter
import json

def chunk_qna(json_path):
    with open(json_path) as f:
        data = json.load(f)

    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=500,
        chunk_overlap=50
    )

    docs = []
    for item in data:
        qa_text = f"Q: {item['question']}\nA: {item['answer']}"
        chunks = text_splitter.split_text(qa_text)
        for chunk in chunks:
            docs.append({
                "content": chunk,
                "metadata": {"question": item['question']}
            })

    with open("chunked.json", "w") as f:
        json.dump(docs, f, indent=2)

if __name__ == "__main__":
    chunk_qna("../processed/clean_translated.json")
