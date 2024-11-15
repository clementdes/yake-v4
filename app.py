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
    .stAlert {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 0.5rem;
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

# Fonction pour l'analyse SERP
def analyze_serp(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None):
    if not valueserp_api_key:
        st.error("Clé API ValueSERP manquante.")
        return None
    
    base_url = "https://api.valueserp.com/search"
    params = {
        "api_key": valueserp_api_key,
        "q": keyword,
        "location": location,
        "num": 30,
        "output": "json"
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        search_results = response.json()
        
        if 'organic_results' not in search_results:
            st.error("Aucun résultat organique trouvé.")
            return None
            
        results = search_results['organic_results']
        urls = [result['link'] for result in results]
        
        # Analyse des URLs avec TextRazor
        all_keywords = []
        all_topics = []
        all_entities = []
        
        for url in urls[:10]:  # Limiter à 10 URLs pour la performance
            text, topics, entities, _ = enhanced_textrazor_analysis(url, textrazor_api_key)
            if text:
                kw_extractor = yake.KeywordExtractor(
                    lan="fr",
                    n=3,
                    dedupLim=0.9,
                    top=20
                )
                keywords = kw_extractor.extract_keywords(text)
                all_keywords.extend(keywords)
                if topics:
                    all_topics.extend(topics)
                if entities:
                    all_entities.extend(entities)
        
        # Analyse de l'URL de l'utilisateur si fournie
        user_data = None
        if user_url:
            user_text, user_topics, user_entities, _ = enhanced_textrazor_analysis(user_url, textrazor_api_key)
            if user_text:
                user_keywords = kw_extractor.extract_keywords(user_text)
                user_data = {
                    'keywords': user_keywords,
                    'topics': user_topics,
                    'entities': user_entities
                }
        
        return {
            'urls': urls,
            'keywords': all_keywords,
            'topics': all_topics,
            'entities': all_entities,
            'user_data': user_data
        }
        
    except requests.RequestException as e:
        st.error(f"Erreur lors de la requête SERP : {e}")
        return None

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

# Pages
if page == "Analyse de Texte":
    st.title("Analyse de Texte Avancée")
    
    text_input = st.text_area("Entrez votre texte ici:", height=200)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Analyser le texte"):
            if text_input.strip():
                kw_extractor = yake.KeywordExtractor(
                    lan=language,
                    n=3,
                    dedupLim=0.9,
                    top=max_keywords,
                    features=None
                )
                keywords = kw_extractor.extract_keywords(text_input)
                
                df = pd.DataFrame(keywords, columns=['Mot-clé', 'Score'])
                df['Occurrences'] = df['Mot-clé'].apply(lambda x: text_input.lower().count(x.lower()))
                
                st.subheader("Résultats de l'analyse")
                st.dataframe(df)
                
                st.plotly_chart(create_keywords_chart(df))
                
                wordcloud_image = generate_wordcloud(text_input)
                st.image(wordcloud_image)
                
                save_analysis_history({
                    'text': text_input[:200] + '...',
                    'keywords': df.to_dict('records')
                }, 'text_analysis')

elif page == "Analyse d'URL":
    st.title("Analyse d'URL")
    textrazor_api_key = st.text_input("Clé API TextRazor", type="password")
    url_input = st.text_input("Entrez l'URL à analyser:")
    
    if st.button("Analyser l'URL"):
        if url_input and textrazor_api_key:
            text, topics, entities, semantic_data = enhanced_textrazor_analysis(url_input, textrazor_api_key)
            if text:
                st.subheader("Contenu extrait")
                st.write(text[:500] + "...")
                
                if topics:
                    st.subheader("Topics identifiés")
                    st.write(", ".join(topics))
                
                if entities:
                    st.subheader("Entités identifiées")
                    entities_df = pd.DataFrame(entities, columns=['Entité', 'Occurrences', 'Score'])
                    st.dataframe(entities_df)
                
                save_analysis_history({
                    'url': url_input,
                    'topics': topics,
                    'entities': entities
                }, 'url_analysis')

elif page == "Recherche SERP":
    st.title("Analyse SERP")
    
    col1, col2 = st.columns(2)
    with col1:
        valueserp_api_key = st.text_input("Clé API ValueSERP", type="password")
        textrazor_api_key = st.text_input("Clé API TextRazor", type="password")
    
    with col2:
        keyword = st.text_input("Mot-clé à analyser:")
        location = st.text_input("Localisation (ex: France):")
        user_url = st.text_input("Votre URL (optionnel):")
    
    if st.button("Analyser les SERP"):
        if keyword and location and valueserp_api_key and textrazor_api_key:
            with st.spinner("Analyse en cours..."):
                results = analyze_serp(keyword, location, valueserp_api_key, textrazor_api_key, user_url)
                
                if results:
                    st.subheader("URLs analysées")
                    st.write(results['urls'])
                    
                    if results['keywords']:
                        st.subheader("Mots-clés principaux")
                        keywords_df = pd.DataFrame(results['keywords'], columns=['Mot-clé', 'Score'])
                        st.dataframe(keywords_df)
                        
                        st.plotly_chart(create_keywords_chart(keywords_df))
                    
                    if results['topics']:
                        st.subheader("Topics principaux")
                        topics_counter = Counter(results['topics'])
                        topics_df = pd.DataFrame(topics_counter.most_common(), columns=['Topic', 'Occurrences'])
                        st.dataframe(topics_df)
                    
                    if results['user_data']:
                        st.subheader("Analyse de votre URL")
                        st.write("Comparaison avec les concurrents")
                        
                        user_keywords_df = pd.DataFrame(results['user_data']['keywords'], columns=['Mot-clé', 'Score'])
                        st.dataframe(user_keywords_df)
                    
                    save_analysis_history({
                        'keyword': keyword,
                        'location': location,
                        'results': results
                    }, 'serp_analysis')

elif page == "Historique des Analyses":
    st.title("Historique des Analyses")
    
    if 'analysis_history' in st.session_state and st.session_state.analysis_history:
        for entry in st.session_state.analysis_history:
            with st.expander(f"{entry['type']} - {entry['date']}"):
                st.json(entry['data'])
    else:
        st.info("Aucun historique d'analyse disponible.")

elif page == "Configuration":
    st.title("Configuration")
    
    st.subheader("APIs")
    valueserp_api_key = st.text_input("Clé API ValueSERP par défaut", type="password")
    textrazor_api_key = st.text_input("Clé API TextRazor par défaut", type="password")
    
    if st.button("Sauvegarder la configuration"):
        st.session_state.valueserp_api_key = valueserp_api_key
        st.session_state.textrazor_api_key = textrazor_api_key
        st.success("Configuration sauvegardée avec succès!")

if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2024 SEO Content Analyzer Pro")
