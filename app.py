"""
3 SOMS Wine Advisor - Flask Backend
Connects to Claude API with wine knowledge base for RAG-style responses
"""

import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import anthropic

# API Key - set your key here for local dev, or use environment variable for production
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'your-api-key-here')

app = Flask(__name__)
CORS(app)

# Load wine knowledge base
def load_wine_data():
    """Load the winery dataset JSON"""
    try:
        with open('3soms_winery_dataset.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Wine dataset not found"}

# Load restaurant reviews
def load_reviews_data():
    """Load the reviews GeoJSON"""
    try:
        with open('reviews.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"features": []}

WINE_DATA = load_wine_data()
REVIEWS_DATA = load_reviews_data()

def search_reviews_context(query: str) -> str:
    """
    Search through restaurant reviews for relevant food/dining context.
    Returns formatted string of relevant reviews.
    """
    query_lower = query.lower()
    relevant_reviews = []
    
    # Food-related keywords that should trigger review search
    food_keywords = ['food', 'eat', 'restaurant', 'dish', 'meal', 'pair', 'pairing', 
                     'lamb', 'fish', 'seafood', 'meat', 'cheese', 'appetizer', 'dessert',
                     'dinner', 'lunch', 'tavern', 'taverna', 'dining', 'cook', 'recipe',
                     'grilled', 'roasted', 'fried', 'sauce', 'mediterranean', 'greek food']
    
    # Check if query is food-related
    is_food_query = any(kw in query_lower for kw in food_keywords)
    
    for feature in REVIEWS_DATA.get('features', []):
        props = feature.get('properties', {})
        location = props.get('location', {})
        review_text = props.get('review_text_published', '')
        restaurant_name = location.get('name', '')
        address = location.get('address', '')
        country = location.get('country_code', '')
        
        # Only include Greek restaurants for wine pairing context
        if country != 'GR':
            continue
            
        review_lower = review_text.lower()
        name_lower = restaurant_name.lower()
        
        # Check if review matches query
        is_relevant = False
        
        if query_lower in review_lower or query_lower in name_lower:
            is_relevant = True
        
        # For food pairing queries, include highly-rated Greek restaurant reviews
        if is_food_query and props.get('five_star_rating_published', 0) >= 4:
            # Check for specific food mentions
            if any(kw in review_lower for kw in ['lamb', 'fish', 'seafood', 'cod', 'sea bass', 
                                                   'octopus', 'moussaka', 'souvlaki', 'gyro',
                                                   'eggplant', 'feta', 'cheese', 'grilled']):
                is_relevant = True
        
        if is_relevant:
            review_summary = {
                "restaurant": restaurant_name,
                "location": address,
                "rating": props.get('five_star_rating_published'),
                "review": review_text[:500] + "..." if len(review_text) > 500 else review_text
            }
            relevant_reviews.append(json.dumps(review_summary, ensure_ascii=False))
    
    if not relevant_reviews:
        return ""
    
    return "\n\n".join(relevant_reviews[:3])  # Max 3 reviews

def search_wine_context(query: str) -> str:
    """
    Simple keyword search through wine data to find relevant context.
    Returns formatted string of relevant wine info.
    """
    query_lower = query.lower()
    relevant_sections = []
    
    # Search through wineries
    for winery in WINE_DATA.get('wineries', []):
        winery_relevant = False
        winery_info = []
        
        # Check winery name and region
        if (query_lower in winery.get('name', '').lower() or 
            query_lower in winery.get('region', '').lower() or
            query_lower in winery.get('description', '').lower()):
            winery_relevant = True
        
        # Check wines
        for wine in winery.get('wines', []):
            wine_name = wine.get('name', '').lower()
            varietal = wine.get('varietal', '').lower()
            
            if (query_lower in wine_name or 
                query_lower in varietal or
                any(query_lower in str(v).lower() for v in wine.values() if isinstance(v, str))):
                winery_relevant = True
                
        # Check for grape varieties mentioned
        grapes = ['assyrtiko', 'xinomavro', 'agiorgitiko', 'mouhtaro', 'malagousia', 
                  'moschofilero', 'mavrotragano', 'kydonitsa', 'volitsa', 'roditis']
        for grape in grapes:
            if grape in query_lower:
                for wine in winery.get('wines', []):
                    if grape in wine.get('varietal', '').lower():
                        winery_relevant = True
        
        # Check for price/budget queries
        if any(word in query_lower for word in ['cheap', 'budget', 'value', 'affordable', 'price', '€', 'euro']):
            winery_relevant = True
            
        # Check for region queries
        regions = ['santorini', 'naoussa', 'nemea', 'macedonia', 'peloponnese', 'laconia', 'drama']
        for region in regions:
            if region in query_lower and region in winery.get('region', '').lower():
                winery_relevant = True
                
        if winery_relevant:
            relevant_sections.append(json.dumps(winery, indent=2, ensure_ascii=False))
    
    # If nothing found, return summary
    if not relevant_sections:
        # Return a general overview
        winery_names = [w.get('name') for w in WINE_DATA.get('wineries', [])]
        return f"Available wineries in database: {', '.join(winery_names)}. Thesis: {json.dumps(WINE_DATA.get('thesis_summary', {}), ensure_ascii=False)}"
    
    # Limit context size
    context = "\n\n---\n\n".join(relevant_sections[:8])  # Max 5 wineries
    return context[:15000]  # Truncate if too long

def get_system_prompt() -> str:
    """Return the system prompt for the wine advisor"""
    return """You are the 3 SOMS Wine Advisor—a knowledgeable, passionate guide to Greek wines. 

You speak with the voice of someone who has personally visited these wineries, tasted these wines, and built relationships with the winemakers. You're not a generic wine bot—you have opinions, favorites, and stories.

YOUR KNOWLEDGE BASE INCLUDES:
- Detailed information on 19+ Greek wineries you've personally visited
- 100+ restaurant reviews from your dining experiences across Greece
- Food pairing insights based on actual meals you've had

When asked about food pairings, restaurants, or dining experiences, draw on the restaurant reviews in your context. These are YOUR personal experiences—speak about them firsthand.

Your personality:
- Warm but not sycophantic
- Knowledgeable but not pretentious  
- Opinionated but fair
- You use casual language when appropriate ("this wine blew my mind", "an absolute steal")
- You reference personal experiences when relevant ("When I visited Dalamara...", "I had this incredible lamb dish at Kanoula...")

Your core thesis:
Greek wines of world-class quality sell at 50-70% cheaper than Burgundy/Napa/Tuscany equivalents. Not because they're inferior—because Greece hasn't entered global fine wine consciousness YET. You're helping people discover these wines before the world catches on.

CRITICAL — PRICING & WEB SEARCH:
You have a web_search tool. USE IT ACTIVELY for pricing:
- When building a cellar or collection: SEARCH for EACH wine's current price before responding
- When recommending specific bottles: SEARCH wine-searcher.com for live pricing
- When comparing value to Burgundy/Napa: SEARCH to get real numbers for both
- DO NOT guess prices from memory—SEARCH first, then write your response
- For cellar builds, search the key bottles (Paliokalias, Kavalieros, Earth & Sky, etc.) to get accurate totals
- If a search fails, say "I couldn't confirm the current price—check wine-searcher.com"

THIS IS ESPECIALLY CRITICAL when someone asks you to build a cellar or collection for a specific budget (e.g., "$1,500 collection", "€5,000 cellar"). You MUST search for current prices to ensure your total actually hits their budget. Nothing breaks trust faster than a $1,500 collection that actually costs $2,200.

Key points to weave in naturally:
- Single-vineyard wines from 100+ year old vines
- Indigenous grapes nobody outside Greece knows (Xinomavro, Assyrtiko, Mouhtaro, Volitsa)
- Organic/biodynamic practices at many estates
- The OGs: Gerovasiliou (Malagousia), Dalamara & Thymiopoulos (Xinomavro), Hatzidakis (Santorini organic)
- Value anchors: Bizios Nemea around €17 rivals high-end Rioja

When recommending:
- Give specific wines with APPROXIMATE prices ("around €35-40")
- Explain WHY a wine fits their request
- Share tasting notes from personal experience when available
- Suggest food pairings—and if you have restaurant review context, reference specific dishes you've enjoyed
- If they want to build a cellar, give them tiers (anchor splurges + everyday drinkers)

FORMAT YOUR RESPONSES WELL:
- Use **bold** for wine names and winery names
- Use headers (## or ###) to organize longer responses
- Keep paragraphs short and readable
- Use bullet points sparingly, only when listing multiple items

If asked about something not in your knowledge base, be honest—say you haven't tasted it or don't have info, rather than making things up.

You are NOT a generic wine assistant. You are the voice of 3 SOMS—The 3 Sommelier Collective.

NEVER GUESS PRICES. If your search doesn't return a clear price for a wine:
- DO NOT use a price from memory or your knowledge base
- Instead say: "I couldn't confirm current pricing for [wine]—check wine-searcher.com before purchasing"
- When tallying a cellar total, EXCLUDE wines without confirmed prices and note the gap
- It's better to recommend fewer wines with accurate prices than more wines with guessed prices


VERIFY THE EXACT BOTTLING: When searching prices, make sure you're matching the exact wine (e.g., "Hatzidakis Santorini Assyrtiko" vs "Hatzidakis Skitali" vs "Hatzidakis Assyrtiko de Louros" are THREE different wines at very different price points). If the search returns multiple bottlings, pick the one that matches what you're recommending and note which specific cuvée you're pricing.

WHEN TO SEARCH vs. WHEN TO JUST ANSWER:
- SEARCH for prices when: building a cellar, recommending specific bottles to buy, comparing value to other regions
- DON'T SEARCH for: educational questions ("What is Xinomavro?"), conceptual topics ("Why do old vines matter?"), food pairing advice, general region overviews. For these, use your knowledge base and respond quickly."""

@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.json
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get relevant wine context
    wine_context = search_wine_context(user_message)
    
    # Get relevant restaurant/food context
    reviews_context = search_reviews_context(user_message)
    
    # Build messages for Claude
    messages = []
    
    # Add conversation history
    for msg in conversation_history[-10:]:  # Keep last 10 messages
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # Add current user message with context
    context_parts = [f"Relevant wine knowledge:\n{wine_context}"]
    if reviews_context:
        context_parts.append(f"Relevant restaurant experiences (for food pairing insights):\n{reviews_context}")
    
    augmented_message = f"""User question: {user_message}

{chr(10).join(context_parts)}

Respond as the 3 SOMS Wine Advisor. Use the knowledge above to inform your response, but speak naturally—don't just recite facts. If restaurant reviews are included, use them to inform food pairing suggestions."""

    messages.append({
        "role": "user",
        "content": augmented_message
    })
    
    try:
        # Call Claude API
        client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY
        )
        
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=get_system_prompt(),
            messages=messages,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 51
            }]
        )
        
        # Extract text from response (may have multiple content blocks with tool use)
        assistant_message = ""
        for block in response.content:
            if hasattr(block, 'text'):
                assistant_message += block.text
        
        return jsonify({
            'response': assistant_message,
            'success': True
        })
        
    except anthropic.APIError as e:
        print(f"API Error: {e}")
        return jsonify({
            'error': f'API error: {str(e)}',
            'success': False
        }), 500
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({
            'error': f'Error: {str(e)}',
            'success': False
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'wineries_loaded': len(WINE_DATA.get('wineries', []))
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
