from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


#

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Cache for storing scraped content
content_cache = {}

def scrape_concordia_pages():
    if content_cache:  # Return cached content if available
        return content_cache
    
    base_urls = [
        "https://www.concordia.ca/students.html",
        "https://www.concordia.ca/academics.html",
        "https://www.concordia.ca/students/success.html",
        "https://www.concordia.ca/students/financial-support.html",
        "https://www.concordia.ca/admissions.html"
    ]
    
    all_content = []
    
    for url in base_urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text(separator=' ', strip=True)
            all_content.append(text)
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    content_cache['data'] = ' '.join(all_content)
    return content_cache

@app.route('/api/query', methods=['POST'])
def query():
    try:
        data = request.json
        user_query = data.get('query')
        
        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Get context from Concordia pages
        context = scrape_concordia_pages().get('data', '')
        
        # Create a more detailed prompt with RAG
        messages = [
            {"role": "system", "content": """You are ConuAI, a knowledgeable assistant for Concordia University students. 
             Use the provided context to give detailed, accurate answers about Concordia University, Montreal, and student life. 
             If the context doesn't contain relevant information, use your general knowledge but clearly indicate this.
             Always maintain a helpful, friendly tone and provide structured, comprehensive responses."""},
            {"role": "user", "content": f"""Context about Concordia University:
             {context[:3000]}  # Limiting context to avoid token limits
             
             Question: {user_query}
             
             Please provide a detailed response with relevant information from the context when available."""}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500,  # Increased token limit for more detailed responses
            presence_penalty=0.6,  # Encourage more diverse responses
            frequency_penalty=0.3  # Reduce repetition
        )
        
        return jsonify({'response': response.choices[0].message.content.strip()})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Something went wrong'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 