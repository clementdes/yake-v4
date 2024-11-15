import requests
import pandas as pd
from collections import Counter
from .text_analysis import analyze_text_with_textrazor, extract_keywords
import concurrent.futures
import time

def analyze_url_content(url, textrazor_api_key):
    """Analyse le contenu d'une URL avec TextRazor et YAKE."""
    try:
        text, topics, entities_df = analyze_text_with_textrazor(url, textrazor_api_key, is_url=True)
        if text:
            keywords_df = extract_keywords(text)
            return {
                'url': url,
                'text': text,
                'keywords': keywords_df.to_dict('records'),
                'topics': topics,
                'entities': entities_df.to_dict('records') if not entities_df.empty else []
            }
    except Exception as e:
        print(f"Erreur lors de l'analyse de {url}: {str(e)}")
    return None

def analyze_serp_results(keyword, location, valueserp_api_key, textrazor_api_key, user_url=None):
    """Analyse les résultats SERP avec ValueSERP et TextRazor."""
    if not valueserp_api_key or not textrazor_api_key:
        return None
    
    try:
        # Récupération des résultats SERP
        params = {
            "api_key": valueserp_api_key,
            "q": keyword,
            "location": location,
            "num": 30,
            "output": "json"
        }
        
        response = requests.get("https://api.valueserp.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        
        if 'organic_results' not in results:
            return None
            
        urls = [result['link'] for result in results['organic_results']]
        
        # Analyse parallèle des 10 premiers résultats
        analyzed_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(analyze_url_content, url, textrazor_api_key): url 
                for url in urls[:10]
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result:
                    analyzed_results.append(result)
                time.sleep(1)  # Respect des limites d'API
        
        # Analyse de l'URL de l'utilisateur si fournie
        user_data = None
        if user_url:
            user_result = analyze_url_content(user_url, textrazor_api_key)
            if user_result:
                user_data = user_result
        
        # Agrégation des résultats
        all_keywords = []
        all_topics = []
        all_entities = []
        
        for result in analyzed_results:
            all_keywords.extend(result['keywords'])
            if result['topics']:
                all_topics.extend(result['topics'])
            if result['entities']:
                all_entities.extend(result['entities'])
        
        # Calcul des statistiques
        keyword_stats = {}
        for kw in all_keywords:
            keyword = kw['keyword']
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    'keyword': keyword,
                    'total_occurrences': 0,
                    'score': kw['score'],
                    'urls_count': 0
                }
            keyword_stats[keyword]['total_occurrences'] += kw['occurrences']
            keyword_stats[keyword]['urls_count'] += 1
        
        # Création des DataFrames
        keywords_df = pd.DataFrame(list(keyword_stats.values()))
        if not keywords_df.empty:
            keywords_df['average_occurrences'] = keywords_df['total_occurrences'] / keywords_df['urls_count']
            keywords_df = keywords_df.sort_values('total_occurrences', ascending=False)
        
        topics_counter = Counter(all_topics)
        topics_df = pd.DataFrame(topics_counter.most_common(), columns=['topic', 'count'])
        
        entities_df = pd.DataFrame(all_entities)
        if not entities_df.empty:
            entities_df = entities_df.groupby('entity').agg({
                'count': 'sum',
                'relevance': 'mean'
            }).reset_index()
            entities_df = entities_df.sort_values('count', ascending=False)
        
        return {
            'urls': urls,
            'keywords': keywords_df.to_dict('records') if not keywords_df.empty else [],
            'topics': topics_df.to_dict('records') if not topics_df.empty else [],
            'entities': entities_df.to_dict('records') if not entities_df.empty else [],
            'analyzed_results': analyzed_results,
            'user_data': user_data
        }
        
    except requests.RequestException as e:
        print(f"Erreur SERP: {str(e)}")
        return None
