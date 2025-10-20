import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Die URL der Webseite, die gecrawlt werden soll
start_url = 'https://amb.uni-leipzig.de/startseite-bekanntmachungen.html?kat_id=2314'

# Datenextraktion

document_data = []
first_h3_text = None

try:
    response = requests.get(start_url, timeout=5)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    first_h3_tag = soup.find('h3')
    if first_h3_tag:
        first_h3_text = first_h3_tag.get_text(strip=True)
    
    # Finde das Elternelement der aktuellen Dokumente mit der ID 'document-list'
    document_list_div = soup.find('div', id='document-list')
    
    if document_list_div:
        # Suche nur innerhalb dieses Containers nach allen 'document'-Divs
        document_divs = document_list_div.find_all('div', class_='document')

        if not document_divs:
            print("Keine 'document' Elemente gefunden.")
        
        for doc_div in document_divs:
            title_tag = doc_div.find('p', class_='document__title')
            link_tag = doc_div.find('a', class_='document__download', href=True)
            
            if title_tag and link_tag:
                title_text = title_tag.get_text(strip=True)
                absolute_link = urljoin(start_url, link_tag['href'])
                
                document_data.append({
                    'titel': title_text,
                    'link': absolute_link
                })
    else:
        print("document-list' wurde nicht gefunden.")
            
except requests.exceptions.RequestException as e:
    print(f"Fehler beim Zugriff auf die Webseite: {e}")


# Ausgabe der gesammelten Daten


if first_h3_text:
    print("--- Gefundene <h3>-Überschrift ---")
    print(first_h3_text)
    print("-" * 20)
else:
    print("Keine <h3>-Überschrift gefunden.")

if document_data:
    print("\n--- Extrahierte Dokumentendaten ---")
    for item in document_data:
        print(f"Titel: {item['titel']}")
        print(f"Link: {item['link']}")
        print("-" * 20)
else:
    print("Es wurden keine Dokumentendaten extrahiert.")