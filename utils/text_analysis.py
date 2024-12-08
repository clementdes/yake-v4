import yake
from textrazor import TextRazor
import pandas as pd
from collections import Counter

def extract_keywords(text, language="fr", max_keywords=20):
    """Extrait les mots-clés d'un texte avec YAKE."""
    kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=3,
        dedupLim=0.9,
        top=max_keywords
    )
    keywords = kw_extractor.extract_keywords(text)
    
    # Créer le DataFrame avec les bonnes colonnes
    df = pd.DataFrame(keywords, columns=['keyword', 'score'])
    df['occurrences'] = df['keyword'].apply(lambda x: text.lower().count(x.lower()))
    df['occurrences_per_1000_words'] = df['occurrences'] * 1000 / len(text.split())
    return df

def analyze_text_with_textrazor(text_or_url, api_key, is_url=False):
    """Analyse un texte ou une URL avec TextRazor."""
    if not api_key:
        return None, None, None
    
    try:
        client = TextRazor(api_key, extractors=["entities", "topics"])
        
        if is_url:
            response = client.analyze_url(text_or_url)
        else:
            response = client.analyze(text_or_url)
            
        # Extraction des topics
        topics = [topic.label for topic in response.topics()]
        
        # Extraction des entités avec comptage sécurisé
        entities = []
        for entity in response.entities():
            count = sum(1 for _ in filter(lambda x: x.matched_text == entity.matched_text, 
                                        response.entities()))
            entities.append({
                'entity': entity.id,
                'count': count,
                'relevance': entity.relevance_score
            })
        
        # Création du DataFrame des entités
        if entities:
            entities_df = pd.DataFrame(entities)
        else:
            entities_df = pd.DataFrame(columns=['entity', 'count', 'relevance'])
            
        return response.cleaned_text if is_url else text_or_url, topics, entities_df
        
    except Exception as e:
        print(f"Erreur TextRazor: {str(e)}")
        return None, None, None
