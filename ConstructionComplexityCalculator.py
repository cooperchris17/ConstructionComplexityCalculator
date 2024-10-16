from flask import Flask, request, render_template, send_file
import stanza
import pandas as pd
import os
import tempfile
import platform
import scipy.stats as stats

app = Flask(__name__)

# Initialize the Stanza pipeline
nlp = stanza.Pipeline("en")

# Function to calculate diversity (Shannon's entropy) of a sentence
def sentence_diversity_calc(tags):
    pairs = [(tags[i], tags[i+1]) for i in range(len(tags) - 1)]
    pair_counts = {pair: pairs.count(pair) for pair in pairs}
    total_pairs = sum(pair_counts.values())
    probabilities = [count / total_pairs for count in pair_counts.values()]
    return stats.entropy(probabilities, base=2)

# Function to calculate the productivity of each sentence
def sentence_productivity_calc(words, tags):
    word_tag_pairs = list(zip(words, tags))
    pair_counts = {pair: word_tag_pairs.count(pair) for pair in word_tag_pairs}
    total_pairs = sum(pair_counts.values())
    probabilities = [count / total_pairs for count in pair_counts.values()]
    H_WT = stats.entropy(probabilities, base=2)
    
    tag_counts = {tag: tags.count(tag) for tag in tags}
    total_tags = sum(tag_counts.values())
    tag_probabilities = [count / total_tags for count in tag_counts.values()]
    H_T = stats.entropy(tag_probabilities, base=2)
    
    H_WT_given_T = H_WT - H_T
    return H_WT_given_T + 1

# Function to calculate the document complexity
def document_complexity_calc(sentences, doc):
    N = len(sentences)
    total_complexity = total_diversity = total_productivity = 0

    for sentence in sentences:
        sen_words = [word.text.lower() for word in sentence.words if word.upos != "PUNCT"]
        sen_pos = [word.xpos for word in sentence.words if word.upos != "PUNCT"]
        
        diversity = sentence_diversity_calc(sen_pos)
        productivity = sentence_productivity_calc(sen_words, sen_pos)
        
        total_complexity += diversity * productivity
        total_diversity += diversity
        total_productivity += productivity

    return total_complexity / N, total_diversity / N, total_productivity / N

def get_downloads_folder():
    if platform.system() == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    elif platform.system() == "Darwin":
        return os.path.join(os.environ["HOME"], "Downloads")
    else:
        return os.path.join(os.environ["HOME"], "Downloads")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    text = request.form['text']
    files = request.files.getlist('files')
    results = []

    if files:
        for uploaded_file in files:
            if not uploaded_file.filename.endswith('.txt'):
                return "Only .txt files are allowed."

            content = uploaded_file.read().decode('utf-8')
            doc = nlp(content)
            complexity, avg_diversity, avg_productivity = document_complexity_calc(doc.sentences, doc)
            results.append({'filename': uploaded_file.filename,
                            'complexity': complexity,
                            'diversity': avg_diversity,
                            'productivity': avg_productivity})

        df = pd.DataFrame(results)
        downloads_folder = get_downloads_folder()
        csv_filename = os.path.join(downloads_folder, 'document_complexity_scores.csv')
        df.to_csv(csv_filename, index=False)

        return "Finished processing, check your downloads folder."

    elif text:
        doc = nlp(text)
        complexity, avg_diversity, avg_productivity = document_complexity_calc(doc.sentences, doc)
        return f"""
        Complexity score: {complexity}<br>
        Diversity: {avg_diversity}<br>
        Productivity: {avg_productivity}
        """

    return "No input provided"


if __name__ == '__main__':
    app.run(debug=True)