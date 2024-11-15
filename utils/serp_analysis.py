import requests
import pandas as pd
from .text_analysis import analyze_text_with_textrazor, extract_keywords

def analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None):
    """Analyse les résultats SERP avec ValueSERP et TextRazor."""
    if not valueserp_api_key:
        return None
    
    params = {
        "api_key": valueserp_api_key,
        "q": keyword,
        "location": location,
        "num": 30,
        "output": "json"
    }
    
    try:
        response = requests.get("https://api.valueserp.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        
        if 'organic_results' not in results:
            return None
            
        urls = [result['link'] for result in results['organic_results']]
        
        # Analyse des URLs
        all_keywords = []
        all_topics = []
        all_entities = pd.DataFrame()
        
        for url in urls[:10]:
            text, topics, entities_df = analyze_text_with_textrazor(url, textrazor_api_key, is_url=True)
            if text:
                keywords_df = extract_keywords(text)
                all_keywords.extend(keywords_df.to_dict('records'))
                if topics:
                    all_topics.extend(topics)
                if not entities_df.empty:
                    all_entities = pd.concat([all_entities, entities_df])
        
        # Analyse de l'URL utilisateur
        user_data = None
        if user_url:
            text, topics, entities_df = analyze_text_with_textrazor(user_url, textrazor_api_key, is_url=True)
            if text:
                user_data = {
                    'keywords': extract_keywords(text).to_dict('records'),
                    'topics': topics,
                    'entities': entities_df.to_dict('records') if not entities_df.empty else []
                }
        
        return {
            'urls': urls,
            'keywords': all_keywords,
            'topics': all_topics,
            'entities': all_entities.to_dict('records') if not all_entities.empty else [],
            'user_data': user_data
        }
        
    except requests.RequestException as e:
        print(f"Erreur SERP: {str(e)}")
        return None