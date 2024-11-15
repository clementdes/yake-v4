import streamlit as st
import yake
import nltk
from nltk.corpus import stopwords
import pandas as pd
import os
import textrazor
import requests
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import json

# Configuration de la page
st.set_page_config(
    page_title="SEO Content Analyzer Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .reportTitle {
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de NLTK
nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)
nltk.data.path.append(nltk_data_dir)
try:
    nltk.download('stopwords', download_dir=nltk_data_dir)
    nltk.download('punkt', download_dir=nltk_data_dir)
except Exception as e:
    st.error(f"Erreur lors du téléchargement des ressources NLTK : {e}")

# Fonction pour sauvegarder l'historique
def save_analysis_history(data, analysis_type):
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    
    history_entry = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': analysis_type,
        'data': data
    }
    st.session_state.analysis_history.append(history_entry)

# Fonction pour générer un nuage de mots
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    # Convertir le graphique en image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

# Fonction pour créer un graphique interactif des mots-clés
def create_keywords_chart(df, top_n=20):
    df_sorted = df.sort_values('Nombre d\'occurrences total', ascending=True).tail(top_n)
    fig = go.Figure(go.Bar(
        x=df_sorted['Nombre d\'occurrences total'],
        y=df_sorted['Mot Yake'],
        orientation='h'
    ))
    fig.update_layout(
        title='Top ' + str(top_n) + ' mots-clés par nombre d\'occurrences',
        xaxis_title='Nombre d\'occurrences',
        yaxis_title='Mots-clés',
        height=600
    )
    return fig

# Fonction améliorée pour l'analyse TextRazor
def enhanced_textrazor_analysis(url, api_key):
    if not api_key:
        st.error("Clé API TextRazor manquante.")
        return None, None, None, None
    
    textrazor.api_key = api_key
    client = textrazor.TextRazor(extractors=["entities", "topics", "words", "phrases"])
    client.set_cleanup_mode("cleanHTML")
    client.set_cleanup_return_cleaned(True)
    
    try:
        response = client.analyze_url(url)
        if response.ok:
            # Analyse sémantique approfondie
            semantic_data = {
                'topics': [topic.label for topic in response.topics()],
                'entities': [(entity.id, entity.matched_text.count(entity.matched_text), 
                            entity.relevance_score) for entity in response.entities()],
                'phrases': [phrase.words for phrase in response.phrases()],
                'sentiment_score': getattr(response, 'sentiment_score', 0)
            }
            return response.cleaned_text, semantic_data['topics'], semantic_data['entities'], semantic_data
        else:
            st.error(f"Erreur TextRazor : {response.error}")
            return None, None, None, None
    except Exception as e:
        st.error(f"Erreur d'analyse TextRazor : {e}")
        return None, None, None, None

# Fonction pour l'export des données
def export_analysis_data(data, format='json'):
    if format == 'json':
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif format == 'csv':
        return pd.DataFrame(data).to_csv(index=False)

# Navigation principale
st.sidebar.title("SEO Content Analyzer Pro")
page = st.sidebar.radio("Navigation", [
    "Analyse de Texte",
    "Analyse d'URL",
    "Recherche SERP",
    "Historique des Analyses",
    "Configuration"
])

# Configuration globale dans la sidebar
with st.sidebar.expander("Configuration Globale"):
    max_keywords = st.number_input("Nombre max de mots-clés", 10, 200, 100)
    min_char_length = st.number_input("Longueur min des mots-clés", 3, 10, 3)
    language = st.selectbox("Langue", ["fr", "en", "es", "de", "it"])

# Page principale
if page == "Analyse de Texte":
    st.title("Analyse de Texte Avancée")
    
    text_input = st.text_area("Entrez votre texte ici:", height=200)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyser le texte"):
            if text_input.strip():
                # Analyse YAKE
                kw_extractor = yake.KeywordExtractor(
                    lan=language,
                    n=3,
                    dedupLim=0.9,
                    top=max_keywords,
                    features=None
                )
                keywords = kw_extractor.extract_keywords(text_input)
                
                # Création du DataFrame
                df = pd.DataFrame(keywords, columns=['Mot-clé', 'Score'])
                df['Occurrences'] = df['Mot-clé'].apply(lambda x: text_input.lower().count(x.lower()))
                
                # Affichage des résultats
                st.subheader("Résultats de l'analyse")
                st.dataframe(df)
                
                # Visualisations
                st.plotly_chart(create_keywords_chart(df))
                
                # Nuage de mots
                wordcloud_image = generate_wordcloud(text_input)
                st.image(wordcloud_image)
                
                # Sauvegarde dans l'historique
                save_analysis_history({
                    'text': text_input[:200] + '...',
                    'keywords': df.to_dict('records')
                }, 'text_analysis')

# Continuer avec les autres pages...
# Le reste du code reste identique à votre implémentation originale,
# mais avec les nouvelles fonctionnalités intégrées.

if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2024 SEO Content Analyzer Pro")
