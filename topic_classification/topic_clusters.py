import numpy as np
import pandas as pd
import re
import operator
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import decomposition

from gensim.models import Word2Vec, phrases, Phrases
from gensim.parsing.preprocessing import STOPWORDS as stop_words

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

import matplotlib as mpl
import matplotlib.pyplot as plt

import spacy
nlp = spacy.load('en_core_web_sm')

import os
from azure.storage.blob import BlobServiceClient
import io

# For PDF extraction
import PyPDF2
from dotenv import load_dotenv
load_dotenv(dotenv_path=".azure/KapGPT-dev/.env")

# Load environment variables or set directly
account_url = f"https://{os.getenv('AZURE_STORAGE_ACCOUNT')}.blob.core.windows.net"
container_name = os.getenv("AZURE_STORAGE_CONTAINER")

credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
container_client = blob_service_client.get_container_client(container_name)

corpus = []

for blob in container_client.list_blobs():
    if blob.name.endswith('.txt') or blob.name.endswith('.pdf'):
        blob_client = container_client.get_blob_client(blob)
        blob_data = blob_client.download_blob().readall()
        if blob.name.endswith('.txt'):
            text = blob_data.decode('utf-8', errors='ignore')
            corpus.append(text)
        elif blob.name.endswith('.pdf'):
            with io.BytesIO(blob_data) as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                pdf_text = ""
                for page in reader.pages:
                    pdf_text += page.extract_text() or ""
                corpus.append(pdf_text)

#input_txt = "\n".join(corpus)
df_corpus = pd.DataFrame({'input_text': corpus})

#### Clean & Preprocess Text

# Function to clean text
def clean_text(txt):
    # exclude meta data, quotes and newline expressions
    excl_meta = re.sub("\n|\'|\s\d+\s+", ' ', txt.split('Lines:')[-1])
    excl_meta = re.sub('In article\s.*writes:?', '', excl_meta)
    excl_meta = re.sub('(distribution:|nntp-posting-host:)\s*\S*\s?', ' ', excl_meta.lower())
    
    # exclude emails and urls
    excl_email = re.sub('\S*@\S*\s?', ' ', excl_meta)
    excl_url = re.sub('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', ' ', excl_email) 
    
    # exclude non-characters and trim text
    excl_nonchar = re.sub('[^a-zA-Z\s]', ' ', excl_url)  
    excl_trim = re.sub('\s\s+', ' ', excl_nonchar).strip()

    return(excl_trim)


# Store all documents (cleaned text) within list
documents = df_corpus['input_text'].map(lambda text: clean_text(text)).tolist()

# # Preview document (cleaned but without text-processing)
# documents[10]

# Lemmatise reviews using spaCy
documents_lemma = []
for document in documents:
    doc_spacy = nlp(document)
    doc_lemma = ' '.join(token.lemma_ for token in doc_spacy if not token.is_stop and token.is_alpha)
    documents_lemma.append(doc_lemma)


# Nested lists of tokens for each document
tokens = [[token for token in doc.split(' ')] for doc in documents_lemma]

# Train bigram model
bigram = Phrases(tokens, min_count=3, threshold=2500)
bigram_mod = phrases.Phraser(bigram)

# Apply bigram model to corpus
tokens_bigrams = [bigram_mod[doc] for doc in tokens]

# +
# List placeholder for post-processed document text
docs_processed = []

# Reconstruct documents (incl bigrams); exclude stopwords (and short/long tokens)
for doc in tokens_bigrams:
    doc = ' '.join([token for token in doc \
                        if (3 < len(token) < 25) \
                            and token not in stop_words])
    docs_processed.append(doc)

# Capture all bigrams (for preview only)
bigram_list = []
[[bigram_list.append(token) \
    for token in doc if re.search('_', token)] \
        for doc in tokens_bigrams]

# Preview top 25 bigrams
for i in sorted(set(bigram_list))[:5]:
    print(i)

len(docs_processed)

# # Comparison of document length (pre, semi and post text processing)
# len(df['comment_cleaned'][1695]), len(documents[1695]), len(docs_processed[1695])
# #len(df['content'][7500]), len(documents[7500]), len(docs_processed[7500])

# #### Token weightings
# Create document-term matrix, weighted by tfidf
tfidf_vectorizer = TfidfVectorizer(min_df=10)
tfidf_model = tfidf_vectorizer.fit(docs_processed)
tfidf_dtm = tfidf_model.transform(docs_processed)

# Tfidf dimensions
print("%d documents and %d tokens" % (tfidf_dtm.shape[0], tfidf_dtm.shape[1]))

# Function to rank token on weighting
def rank_tokens(dtm_matrix, tokens):
    # sum over matrix columns
    sum_cols = dtm_matrix.sum(axis=0)
    
    # dictionary linking weightings to tokens
    weights = {}
    for col, token in enumerate(tokens):
        weights[token] = sum_cols[0, col]
    
    # sort tokens by weight over all documents
    tokens_ranked = sorted(weights.items(), key=operator.itemgetter(1), reverse=True)
    
    return tokens_ranked


# Apply ranking function to weighted dtm
list_tokens = tfidf_vectorizer.get_feature_names_out()
list_ranking = rank_tokens(tfidf_dtm, list_tokens)

# Print top tf-idf tokens
for index_no, pair in enumerate(list_ranking[0:20]):
    print("%02d. %s (%.2f)" % (index_no+1, pair[0], pair[1]))

# #### Identify Number of Topics

# Apply NMF to range of k values
topic_models = []
max_k = min(tfidf_dtm.shape[0], tfidf_dtm.shape[1])
for k in range(1, max_k+1):
    # train model
    nmf_model = decomposition.NMF(init='nndsvd', n_components=k, l1_ratio=.5, alpha_W=.05, alpha_H=.05)
    
    # capture topic and token weightings
    topics_weights = nmf_model.fit_transform(tfidf_dtm)
    tokens_weights = nmf_model.components_
    topic_models.append((k, topics_weights, tokens_weights))


# Class for token generator
class TokeniseReviews:
    def __init__(self, docs):
        self.docs = docs

    def __iter__(self):
        for doc in self.docs:
            tokens = []
            for token in doc.split(' '):
                tokens.append(token)
            yield tokens


# Train skipgram over all documents
token_gen = TokeniseReviews(docs_processed)
sg_model = Word2Vec(token_gen, vector_size=200, window=5, sg=1)


# Function for topic-token similarity
def topic_similarity(sg_model, topic_tokens): 
    overall_sim = 0.0
    for topic_index in range(len(topic_tokens)):   
        
        # measure similarity between topic-token pair combinations
        pair_sim_scores = []
        for pair in combinations(topic_tokens[topic_index], 2):
            pair_sim_scores.append(sg_model.wv.similarity(pair[0], pair[1]))
            
        # average token similarity scores for a given topic
        topic_sim = sum(pair_sim_scores) / len(pair_sim_scores)
        
        # accumulate all topic (mean) similarity scores
        overall_sim += topic_sim
    
    # divide similarity scores by number of topics
    mean_sim = overall_sim / len(topic_tokens)
    
    return mean_sim


# Function to retrieve top-tokens
def get_top_tokens(tokens_all, token_weights, topic_index, top_n):
    # identify indices for top tokens
    top_indices = np.argsort(token_weights[topic_index,:])[::-1]
    
    # indices for top-ranked tokens (and weights)
    top_tokens = []
    top_weights = []
    
    for token_index in top_indices[0:top_n]:
        top_tokens.append(tokens_all[token_index])
        top_weights.append(token_weights[topic_index, token_index])
        
    return top_tokens, top_weights


# List of all tokens (corpus vocabulary)
list_tokens = tfidf_vectorizer.get_feature_names_out()

# Placeholders for similarity scores
k_values = []
similarity_scores = []

# Loop through tuples within list of nmf models
for (k, topic_weights, token_weights) in topic_models:
    
    # For each model, retrieve top tokens (with highest loadings on weight)
    token_rankings = []
    for topic_index in range(k):
        token_rankings.append(get_top_tokens(list_tokens, token_weights, topic_index, 5)[0])
        
    # Measure similarity using skip-gram model
    k_values.append(k)
    similarity_scores.append(topic_similarity(sg_model, token_rankings))

# Plot mean intra-topic token similarity scores
fig = plt.figure(figsize=(10,6))
plt.scatter(k_values, similarity_scores, s=50)
ax = plt.plot(k_values, similarity_scores)
plt.xticks(k_values);

# # #### Fit & Evaluate Final Topic Model

# # Retrain model for specified k
# k = 18
# nmf_model = decomposition.NMF(init='nndsvd', n_components=k, l1_ratio=.5, alpha=.05)

# # Capture topic and token weighting matrices
# topic_weights = nmf_model.fit_transform(tfidf_dtm)
# token_weights = nmf_model.components_

# # Obtain top-n token for each topic
# top_tokens = []
# for topic_index in range(k):
#     top_tokens.append(get_top_tokens(list_tokens, token_weights, topic_index, 3))#10
#     top_tokens_str = ", ".join(top_tokens[topic_index][0])
#     print("Topic %02d: %s" % (topic_index+1, top_tokens_str))


# # Function to plot top topic-tokens
# def plot_top_tokens(top_tokens, top_weights):   
#     # sort tokens
#     top_tokens.reverse()
#     top_weights.reverse()
    
#     # print bar chart
#     ypos = np.arange(len(top_tokens))
#     ax = plt.barh(ypos, top_weights, color='grey', tick_label=top_tokens)
#     plt.tight_layout()
#     plt.show()


# # Plot top 10 tokens for each topic
# for topic_index in range(k):
#     top_tokens, top_weights = get_top_tokens(list_tokens, token_weights, topic_index, 3)
#     plot_top_tokens(top_tokens, top_weights)


# # Function to identify representative documents for specified topic
# def get_doc_examples(all_docs, topic_weights, topic_number, top_n):
#     # sort by weighting
#     top_indices = np.argsort(topic_weights[:,topic_number])[::-1]
    
#     # identify documents for top-ranked indices
#     top_examples = []
#     for doc_index in top_indices[0:top_n]:
#         top_examples.append(all_docs[doc_index])
#     return top_examples


# # Print top n documents for a sepecified topic
# topic_examples = get_doc_examples(df['comment'].tolist(), topic_weights, topic_number=1, top_n=5)
# for i, document in enumerate(topic_examples):
#     print('-- EXAMPLE '+str(i+1)+' '+'--'*50)
#     print(document)

# # #### Miscellaneous (EDA, validation etc)

# # Cross check topic weightings against document (news) sources
# df_eval = pd.concat([df['id'], pd.DataFrame(topic_weights)], axis=1)
# df_melt = pd.melt(df_eval, id_vars='id', value_vars=df_eval.columns[1:])
# df_grpd = df_melt.groupby(['variable', 'id'])['value'].mean().reset_index().sort_values(['variable', 'value'], ascending=False)
# df_grpd = df_grpd.groupby('variable').first().reset_index().sort_values('variable', ascending=True)

# # +
# # Capture all top topic-tokens into dictionary
# topn_tokens = []
# dict_tokens = {}

# for topic_index in range(k):
#     topn_tokens.append(get_top_tokens(list_tokens, token_weights, topic_index, 3)) #10
#     top_tokens_str = ", ".join(topn_tokens[topic_index][0])
#     dict_tokens.setdefault(topic_index, []).append(top_tokens_str)

# # +
# # Concatenate top tokens to dataframe of topics
# df_topics = pd.concat([df_grpd, pd.DataFrame.from_dict(dict_tokens, orient='index')], axis=1).drop(['value'], axis=1)
# df_topics.columns = ['Topic', 'Source', 'Top_Tokens']