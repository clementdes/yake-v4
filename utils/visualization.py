import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import pandas as pd

def create_keywords_chart(keywords_data, top_n=20):
    """Crée un graphique des mots-clés les plus fréquents."""
    if isinstance(keywords_data, list):
        df = pd.DataFrame(keywords_data)
    else:
        df = keywords_data
    
    # Assurer que les colonnes existent
    if 'keyword' not in df.columns or 'occurrences' not in df.columns:
        return None
        
    df_sorted = df.sort_values('occurrences', ascending=True).tail(top_n)
    
    fig = go.Figure(go.Bar(
        x=df_sorted['occurrences'],
        y=df_sorted['keyword'],
        orientation='h'
    ))
    
    fig.update_layout(
        title=f'Top {top_n} mots-clés par nombre d\'occurrences',
        xaxis_title='Nombre d\'occurrences',
        yaxis_title='Mots-clés',
        height=600
    )
    
    return fig

def generate_wordcloud(text):
    """Génère un nuage de mots à partir d'un texte."""
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf