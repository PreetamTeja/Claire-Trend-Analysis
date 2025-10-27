# Complete Enhanced Fashion Trend Dashboard with Comprehensive Reports
import dash
from dash import dcc, html, Input, Output, callback, State, ALL, ctx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import warnings
from pytrends.request import TrendReq
import time
from datetime import datetime
import json
import os
import re
from bs4 import BeautifulSoup, Comment
from urllib.parse import quote_plus, urljoin, urlparse
from collections import Counter
import markdown

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize PyTrends
pytrend = TrendReq(hl='en-IN', tz=330)
SERPER_API_KEY = "a25d059942f58d6fd175c3a4060b902d79759e59"  

# State corrections for map compatibility
state_corrections = {
    "Odisha": "Orissa",
    "Delhi": "NCT of Delhi",
    "Puducherry": "Pondicherry",
    "Uttarakhand": "Uttaranchal"
}

# Download India GeoJSON
geojson_url = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
try:
    geojson_data = requests.get(geojson_url, timeout=10).json()
except:
    print("Warning: Could not load GeoJSON data. Map functionality may be limited.")
    geojson_data = None

def fetch_single_keyword_data(keyword):
    """Fetch trends data for a single keyword"""
    print(f"Fetching trends data for: {keyword} at {datetime.now()}")
    
    time_df = pd.DataFrame()
    region_df = pd.DataFrame()
    related_df = pd.DataFrame()
    
    try:
        # Build payload for the keyword
        pytrend.build_payload([keyword], geo='IN', timeframe='today 12-m')
        
        # Get time series data
        df_time = pytrend.interest_over_time()
        if not df_time.empty:
            time_df = df_time[[keyword]].rename(columns={keyword: 'value'})
            time_df['term'] = keyword
            time_df['date'] = df_time.index
            time_df.reset_index(drop=True, inplace=True)
        
        # Get regional data
        df_region = pytrend.interest_by_region(resolution='REGION', inc_low_vol=True)
        if not df_region.empty:
            region_df = df_region[[keyword]].rename(columns={keyword: 'value'})
            region_df['region'] = df_region.index
            region_df['term'] = keyword
            # Apply state name corrections
            region_df['region'] = region_df['region'].replace(state_corrections)
            region_df.reset_index(drop=True, inplace=True)
        
        # Get related queries
        try:
            related = pytrend.related_queries()
            if related.get(keyword) and related[keyword].get('top') is not None:
                related_df = related[keyword]['top']
                related_df['term'] = keyword
        except:
            print(f"No related queries found for {keyword}")
        
        print(f"Data fetching completed for: {keyword}")
        return time_df, region_df, related_df
        
    except Exception as e:
        print(f"Error processing {keyword}: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def fetch_comprehensive_trend_data(keyword):
    """Fetch comprehensive trends data for multiple time periods and related keywords"""
    print(f"Fetching comprehensive data for: {keyword}")
    
    # Define time periods
    time_periods = {
        '1_day': 'now 1-d',
        '7_days': 'now 7-d', 
        '1_month': 'today 1-m',
        '3_months': 'today 3-m',
        '6_months': 'today 6-m',
        '12_months': 'today 12-m'
    }
    
    comprehensive_data = {
        'keyword': keyword,
        'time_periods': {},
        'related_keywords': {},
        'regional_data': {},
        'timestamp': datetime.now().isoformat()
    }
    
    # Fetch data for each time period
    for period_name, timeframe in time_periods.items():
        try:
            print(f"Fetching data for {period_name}...")
            pytrend.build_payload([keyword], geo='IN', timeframe=timeframe)
            
            # Get time series data
            df_time = pytrend.interest_over_time()
            if not df_time.empty:
                time_data = df_time[[keyword]].rename(columns={keyword: 'value'})
                time_data['date'] = df_time.index
                time_data['period'] = period_name
                comprehensive_data['time_periods'][period_name] = time_data.to_dict('records')
            
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching {period_name}: {str(e)}")
            comprehensive_data['time_periods'][period_name] = []
    
    # Fetch regional data (using 12-month timeframe)
    try:
        pytrend.build_payload([keyword], geo='IN', timeframe='today 12-m')
        df_region = pytrend.interest_by_region(resolution='REGION', inc_low_vol=True)
        if not df_region.empty:
            region_data = df_region[[keyword]].rename(columns={keyword: 'value'})
            region_data['region'] = df_region.index
            region_data['region'] = region_data['region'].replace(state_corrections)
            comprehensive_data['regional_data'] = region_data.to_dict('records')
    except Exception as e:
        print(f"Error fetching regional data: {str(e)}")
        comprehensive_data['regional_data'] = []
    
    # Fetch related queries and their data
    try:
        related = pytrend.related_queries()
        if related.get(keyword) and related[keyword].get('top') is not None:
            related_queries = related[keyword]['top']['query'].head(5).tolist()
            
            for related_keyword in related_queries:
                print(f"Fetching data for related keyword: {related_keyword}")
                related_data = {}
                
                # Fetch data for key time periods for related keywords
                key_periods = ['1_month', '3_months', '6_months']
                for period_name in key_periods:
                    timeframe = time_periods[period_name]
                    try:
                        pytrend.build_payload([related_keyword], geo='IN', timeframe=timeframe)
                        df_related = pytrend.interest_over_time()
                        if not df_related.empty:
                            related_time_data = df_related[[related_keyword]].rename(columns={related_keyword: 'value'})
                            related_time_data['date'] = df_related.index
                            related_time_data['period'] = period_name
                            related_data[period_name] = related_time_data.to_dict('records')
                        time.sleep(2)
                    except:
                        related_data[period_name] = []
                
                comprehensive_data['related_keywords'][related_keyword] = related_data
                
    except Exception as e:
        print(f"Error fetching related keywords: {str(e)}")
        comprehensive_data['related_keywords'] = {}
    
    print("Comprehensive data fetching completed")
    return comprehensive_data

def fetch_state_wise_trends(keyword, state_code='IN'):
    """Fetch trends data for a keyword filtered by Indian state"""
    print(f"Fetching state-wise trends for: {keyword} in {state_code}")
    
    # Indian state geo codes for Google Trends
    state_geo_codes = {
        'Andhra Pradesh': 'IN-AP',
        'Arunachal Pradesh': 'IN-AR', 
        'Assam': 'IN-AS',
        'Bihar': 'IN-BR',
        'Chhattisgarh': 'IN-CT',
        'Goa': 'IN-GA',
        'Gujarat': 'IN-GJ',
        'Haryana': 'IN-HR',
        'Himachal Pradesh': 'IN-HP',
        'Jharkhand': 'IN-JH',
        'Karnataka': 'IN-KA',
        'Kerala': 'IN-KL',
        'Madhya Pradesh': 'IN-MP',
        'Maharashtra': 'IN-MH',
        'Manipur': 'IN-MN',
        'Meghalaya': 'IN-ML',
        'Mizoram': 'IN-MZ',
        'Nagaland': 'IN-NL',
        'Odisha': 'IN-OR',
        'Punjab': 'IN-PB',
        'Rajasthan': 'IN-RJ',
        'Sikkim': 'IN-SK',
        'Tamil Nadu': 'IN-TN',
        'Telangana': 'IN-TG',
        'Tripura': 'IN-TR',
        'Uttar Pradesh': 'IN-UP',
        'Uttarakhand': 'IN-UT',
        'West Bengal': 'IN-WB',
        'Delhi': 'IN-DL',
        'Puducherry': 'IN-PY'
    }
    
    try:
        # Use the provided state code or default to India
        geo_code = state_geo_codes.get(state_code, 'IN')
        
        # Build payload for the keyword with state filter
        pytrend.build_payload([keyword], geo=geo_code, timeframe='today 12-m')
        
        # Get time series data
        time_df = pytrend.interest_over_time()
        state_time_data = pd.DataFrame()
        
        if not time_df.empty:
            state_time_data = time_df[[keyword]].rename(columns={keyword: 'value'})
            state_time_data['term'] = keyword
            state_time_data['state'] = state_code
            state_time_data['date'] = time_df.index
            state_time_data.reset_index(drop=True, inplace=True)
        
        # Get city-level data within the state
        city_df = pytrend.interest_by_region(resolution='CITY', inc_low_vol=True)
        state_city_data = pd.DataFrame()
        
        if not city_df.empty:
            state_city_data = city_df[[keyword]].rename(columns={keyword: 'value'})
            state_city_data['city'] = city_df.index
            state_city_data['term'] = keyword
            state_city_data['state'] = state_code
            state_city_data.reset_index(drop=True, inplace=True)
        
        print(f"State-wise data fetching completed for: {keyword} in {state_code}")
        return state_time_data, state_city_data, state_geo_codes
        
    except Exception as e:
        print(f"Error processing {keyword} for state {state_code}: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), state_geo_codes
    
# Fashion Blog Analyzer Class
class AutomatedFashionAnalyzer:
    def __init__(self, serper_api_key):
        self.serper_api_key = serper_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def discover_fashion_blogs(self, clothing_item):
        """Automatically discover fashion blogs using Serper API"""
        print(f"Discovering fashion blogs for: {clothing_item}")
        
        # Multiple search queries to find diverse blog sources
        search_queries = [
            f"{clothing_item} fashion blog latest trends 2024",
            f"best {clothing_item} styling tips fashion bloggers",
            f"{clothing_item} outfit ideas fashion blog",
            f"trending {clothing_item} designs fashion blog",
            f"{clothing_item} fashion guide blog recommendations"
        ]
        
        discovered_blogs = []
        
        for query in search_queries:
            try:
                search_results = self._serper_search(query)
                for result in search_results:
                    if self._is_fashion_blog(result):
                        discovered_blogs.append(result)
                        
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"Search error for query '{query}': {str(e)}")
                continue
        
        # Remove duplicates based on URL
        unique_blogs = {}
        for blog in discovered_blogs:
            domain = urlparse(blog['link']).netloc
            if domain not in unique_blogs:
                unique_blogs[domain] = blog
        
        final_blogs = list(unique_blogs.values())[:15]  # Limit to top 15
        print(f"Discovered {len(final_blogs)} unique fashion blogs")
        return final_blogs
    
    def _serper_search(self, query):
        """Search using Serper API"""
        url = "https://google.serper.dev/search"
        payload = {
            "q": query,
            "num": 10,
            "gl": "us",
            "hl": "en"
        }
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        results = response.json()
        return results.get('organic', [])
    
    def _is_fashion_blog(self, result):
        """Determine if a search result is a fashion blog"""
        url = result.get('link', '').lower()
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Fashion-related keywords
        fashion_keywords = [
            'fashion', 'style', 'outfit', 'trend', 'clothing', 'apparel',
            'wardrobe', 'designer', 'boutique', 'runway', 'wear', 'dress',
            'lookbook', 'styling', 'chic', 'vogue', 'elle', 'bazaar'
        ]
        
        # Blog indicators
        blog_indicators = ['blog', 'article', 'post', 'guide', 'tips', 'ideas']
        
        # Check if content contains fashion and blog keywords
        content = f"{title} {snippet} {url}"
        fashion_score = sum(1 for keyword in fashion_keywords if keyword in content)
        blog_score = sum(1 for indicator in blog_indicators if indicator in content)
        
        # Exclude non-blog sites
        exclude_domains = ['amazon', 'ebay', 'shopping', 'store', 'shop', 'buy', 'price']
        if any(domain in url for domain in exclude_domains):
            return False
            
        return fashion_score >= 2 and blog_score >= 1
    
    def extract_blog_content(self, blog_info, clothing_item):
        """Extract and analyze content from a fashion blog"""
        print(f"Extracting content from: {blog_info.get('title', 'Unknown')}")
        
        try:
            response = self.session.get(blog_info['link'], timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Extract main content areas
            content_selectors = [
                'article', 'main', '.content', '.post', '.entry-content',
                '.blog-post', '.article-content', '[role="main"]'
            ]
            
            main_content = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    main_content = elements[0]
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            # Extract text content
            text_content = main_content.get_text(separator=' ', strip=True) if main_content else ""
            
            # Clean and filter content
            text_content = re.sub(r'\s+', ' ', text_content)
            text_content = text_content[:5000]  # Limit content length
            
            # Extract specific fashion information
            fashion_data = self._analyze_fashion_content(text_content, clothing_item)
            
            return {
                'source': blog_info.get('title', 'Unknown Blog'),
                'url': blog_info['link'],
                'content_length': len(text_content),
                'raw_content': text_content,
                'fashion_analysis': fashion_data,
                'extraction_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Content extraction failed: {str(e)}")
            return None
    
    def _analyze_fashion_content(self, content, clothing_item):
        """Analyze fashion content to extract trends, styles, and recommendations"""
        content_lower = content.lower()
        
        # Extract colors mentioned in content
        color_patterns = [
            r'\b(red|blue|green|yellow|orange|purple|pink|black|white|gray|grey|brown|beige|navy|maroon|teal|coral|mint|lavender|cream|ivory|gold|silver|rose|burgundy|olive|khaki|tan|sage|mauve|peach|salmon|turquoise|magenta|cyan|lime|indigo|violet|crimson|emerald|sapphire|ruby|amber|pearl|champagne|chocolate|coffee|caramel|honey|vanilla|ash|charcoal|slate|steel|copper|bronze|platinum|wine|plum|berry|cherry|strawberry|blush|nude|dusty|pastel|neon|bright|dark|light|muted|vibrant|bold|soft|warm|cool|earth tone|jewel tone)\b',
            r'\b(floral|polka dot|striped|checkered|plaid|leopard|zebra|animal print|geometric|abstract|solid|plain|textured|embroidered|lace|sequined|beaded|metallic|glittery|matte|glossy|satin|silk|velvet|cotton|linen|wool|cashmere|denim|leather|suede|chiffon|georgette|crepe|jersey)\b'
        ]
        
        colors = []
        for pattern in color_patterns:
            matches = re.findall(pattern, content_lower)
            colors.extend(matches)
        
        # Extract style keywords
        style_keywords = [
            'casual', 'formal', 'elegant', 'chic', 'trendy', 'classic', 'vintage',
            'modern', 'bohemian', 'minimalist', 'edgy', 'feminine', 'masculine',
            'sporty', 'glamorous', 'sophisticated', 'playful', 'romantic', 'bold',
            'subtle', 'statement', 'versatile', 'comfortable', 'fitted', 'loose',
            'oversized', 'cropped', 'long', 'short', 'midi', 'maxi', 'mini'
        ]
        
        found_styles = [style for style in style_keywords if style in content_lower]
        
        # Extract trend words
        trend_indicators = [
            'trending', 'popular', 'hot', 'must-have', 'essential', 'staple',
            'favorite', 'go-to', 'bestseller', 'viral', 'instagram', 'tiktok',
            'celeb', 'celebrity', 'influencer', 'street style', 'runway',
            '2024', 'latest', 'new', 'fresh', 'updated', 'modern'
        ]
        
        trends = [trend for trend in trend_indicators if trend in content_lower]
        
        # Extract brand mentions (look for capitalized words that might be brands)
        brand_pattern = r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b'
        potential_brands = re.findall(brand_pattern, content)
        
        # Filter common non-brand words
        common_words = {'The', 'And', 'But', 'For', 'You', 'Your', 'This', 'That', 'These', 'Those', 'When', 'Where', 'How', 'What', 'Why', 'Who'}
        brands = [brand for brand in potential_brands if brand not in common_words and len(brand) > 2][:10]
        
        # Extract price mentions
        price_pattern = r'[\$₹£€]\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s*(?:dollars|rupees|pounds|euros|INR|USD|GBP|EUR)'
        prices = re.findall(price_pattern, content)
        
        # Extract styling tips (sentences with key styling words)
        styling_words = ['wear', 'pair', 'style', 'match', 'combine', 'accessorize', 'layer']
        sentences = re.split(r'[.!?]+', content)
        styling_tips = []
        
        for sentence in sentences:
            if any(word in sentence.lower() for word in styling_words) and len(sentence.strip()) > 20:
                styling_tips.append(sentence.strip())
                if len(styling_tips) >= 5:
                    break
        
        return {
            'colors': list(set(colors))[:15],
            'styles': list(set(found_styles))[:10],
            'trends': list(set(trends))[:8],
            'brands': list(set(brands))[:10],
            'prices': list(set(prices))[:5],
            'styling_tips': styling_tips[:5],
            'content_relevance': self._calculate_relevance(content_lower, clothing_item)
        }
    
    def _calculate_relevance(self, content, clothing_item):
        """Calculate how relevant the content is to the clothing item"""
        item_mentions = content.lower().count(clothing_item.lower())
        content_length = len(content.split())
        
        if content_length == 0:
            return 0
            
        relevance_score = min((item_mentions / content_length) * 100, 100)
        return round(relevance_score, 2)
    
    def analyze_all_blogs(self, clothing_item):
        """Discover and analyze all fashion blogs for a clothing item"""
        print(f"Starting automated analysis for: {clothing_item}")
        
        # Step 1: Discover blogs
        discovered_blogs = self.discover_fashion_blogs(clothing_item)
        
        if not discovered_blogs:
            print("No fashion blogs discovered")
            return None
        
        # Step 2: Extract content from each blog
        extracted_data = []
        for blog in discovered_blogs:
            content_data = self.extract_blog_content(blog, clothing_item)
            if content_data and content_data['fashion_analysis']['content_relevance'] > 0:
                extracted_data.append(content_data)
            
            time.sleep(2)  # Rate limiting between requests
        
        print(f"Successfully analyzed {len(extracted_data)} blogs")
        return extracted_data
    
    def generate_comprehensive_report(self, clothing_item, blog_data):
        """Generate comprehensive fashion report from analyzed blog content"""
        print("Generating comprehensive fashion report...")
        
        if not blog_data:
            return None
        
        # Aggregate all fashion data
        all_colors = []
        all_styles = []
        all_trends = []
        all_brands = []
        all_prices = []
        all_styling_tips = []
        
        for blog in blog_data:
            analysis = blog['fashion_analysis']
            all_colors.extend(analysis['colors'])
            all_styles.extend(analysis['styles'])
            all_trends.extend(analysis['trends'])
            all_brands.extend(analysis['brands'])
            all_prices.extend(analysis['prices'])
            all_styling_tips.extend(analysis['styling_tips'])
        
        # Count and rank by frequency
        top_colors = [item for item, count in Counter(all_colors).most_common(10)]
        top_styles = [item for item, count in Counter(all_styles).most_common(8)]
        top_trends = [item for item, count in Counter(all_trends).most_common(6)]
        top_brands = [item for item, count in Counter(all_brands).most_common(8)]
        
        # Calculate analysis confidence
        total_content = sum(blog['content_length'] for blog in blog_data)
        avg_relevance = sum(blog['fashion_analysis']['content_relevance'] for blog in blog_data) / len(blog_data)
        confidence_score = min(85, (len(blog_data) * 5) + (avg_relevance * 2))
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""# Fashion Analysis Report: {clothing_item.title()}

## Summary
- **Research Date**: {timestamp}
- **Blogs Analyzed**: {len(blog_data)} fashion blogs
- **Content Analyzed**: {total_content:,} characters
- **Analysis Confidence**: {confidence_score:.1f}%
- **Average Relevance**: {avg_relevance:.1f}%

## Discovered Color Trends
Based on analysis of {len(blog_data)} fashion blogs, the most mentioned colors for {clothing_item} are:

{chr(10).join([f"- **{color.title()}**: Frequently mentioned across multiple fashion sources" for color in top_colors[:8]])}

### Color Trend Analysis
{chr(10).join([f"- {color.title()} appears to be trending in current {clothing_item} fashion" for color in top_colors[:5]])}

## Style Variations Discovered
The following styles were identified from real fashion blog content:

{chr(10).join([f"- **{style.title()}**: Popular styling approach mentioned in fashion blogs" for style in top_styles])}

### Current Style Trends
{chr(10).join([f"- {trend.title()} is mentioned as a current trend" for trend in top_trends])}

## Brand Mentions from Fashion Blogs
These brands were mentioned across the analyzed fashion content:

{chr(10).join([f"- **{brand}**: Referenced in fashion blog content" for brand in top_brands])}

## Styling Tips from Fashion Experts
Real styling advice extracted from fashion blogs:

{chr(10).join([f"- {tip}" for tip in all_styling_tips[:8] if len(tip) > 30])}

## Market Intelligence

### Trend Indicators
{chr(10).join([f"- **{trend.title()}**: Identified as trending in fashion blog discussions" for trend in top_trends])}

### Style Popularity
Based on frequency analysis across {len(blog_data)} sources:
1. **Most Mentioned Style**: {top_styles[0].title() if top_styles else 'Not determined'}
2. **Trending Colors**: {', '.join(top_colors[:3]) if top_colors else 'Various colors mentioned'}
3. **Popular Brands**: {', '.join(top_brands[:3]) if top_brands else 'Multiple brands referenced'}

## Content Sources
The following fashion blogs were analyzed for this report:

{chr(10).join([f"- **{blog['source']}** - {blog['url']} (Relevance: {blog['fashion_analysis']['content_relevance']:.1f}%)" for blog in blog_data])}

## Data Analysis Metrics
- **Total Content Words**: {total_content // 5:,} (estimated)
- **Unique Colors Identified**: {len(set(all_colors))}
- **Style Variations Found**: {len(set(all_styles))}
- **Trend Keywords Detected**: {len(set(all_trends))}
- **Fashion Brands Mentioned**: {len(set(all_brands))}

## Research Methodology
1. **Blog Discovery**: Used Serper API to find relevant fashion blogs
2. **Content Extraction**: Scraped and analyzed actual blog content
3. **Trend Analysis**: Identified patterns in colors, styles, and trends
4. **Brand Recognition**: Extracted brand mentions from content
5. **Confidence Scoring**: Calculated based on content volume and relevance

## Report Metadata
- **Generated**: {timestamp}
- **Analysis Type**: Automated blog content analysis
- **Data Sources**: {len(blog_data)} dynamically discovered fashion blogs
- **Research Scope**: Real-time fashion blog content
- **Update Frequency**: On-demand analysis
- **Version**: Automated Fashion Analyzer v1.0

---
*This report was generated through automated analysis of real fashion blog content. All trends, colors, styles, and recommendations are extracted from actual fashion publications and blogs, ensuring current and relevant fashion intelligence.*
"""
        
        return report

def create_comprehensive_report_visualizations(data):
    """Create comprehensive visualizations from the trend data"""
    if not data:
        return html.Div("No data available")
    
    keyword = data['keyword']
    visualizations = []
    
    # 1. Multi-timeframe comparison chart
    fig_comparison = make_subplots(
        rows=2, cols=3,
        subplot_titles=['1 Day', '7 Days', '1 Month', '3 Months', '6 Months', '12 Months'],
        specs=[[{"secondary_y": False} for _ in range(3)] for _ in range(2)]
    )
    
    positions = [(1,1), (1,2), (1,3), (2,1), (2,2), (2,3)]
    colors_list = ['#6366F1', '#8B5CF6', '#10B981', '#F59E0B', '#06B6D4', '#EF4444']
    
    for i, (period, pos, color) in enumerate(zip(data['time_periods'].keys(), positions, colors_list)):
        period_data = pd.DataFrame(data['time_periods'][period])
        if not period_data.empty:
            period_data['date'] = pd.to_datetime(period_data['date'])
            fig_comparison.add_trace(
                go.Scatter(
                    x=period_data['date'], 
                    y=period_data['value'],
                    mode='lines',
                    name=period.replace('_', ' ').title(),
                    line=dict(color=color, width=2)
                ),
                row=pos[0], col=pos[1]
            )
    
    fig_comparison.update_layout(
        height=600,
        title_text=f"Multi-Timeframe Analysis: {keyword.title()}",
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    visualizations.append(
        html.Div([
            html.H3("Multi-Timeframe Trend Analysis", style={'fontSize': '18px', 'fontWeight': '600', 'color': '#1E293B', 'marginBottom': '16px'}),
            dcc.Graph(figure=fig_comparison, style={'height': '600px'})
        ], style={'backgroundColor': '#FFFFFF', 'padding': '24px', 'borderRadius': '12px', 'border': '1px solid #E2E8F0', 'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)', 'marginBottom': '24px'})
    )
    
    # 2. Related keywords comparison
    if data['related_keywords']:
        fig_related = go.Figure()
        
        for related_kw, periods_data in data['related_keywords'].items():
            if '3_months' in periods_data and periods_data['3_months']:
                kw_data = pd.DataFrame(periods_data['3_months'])
                kw_data['date'] = pd.to_datetime(kw_data['date'])
                
                fig_related.add_trace(
                    go.Scatter(
                        x=kw_data['date'],
                        y=kw_data['value'],
                        mode='lines',
                        name=related_kw,
                        line=dict(width=2)
                    )
                )
        
        fig_related.update_layout(
            title=f"Related Keywords Comparison (3 Months)",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1E293B'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        visualizations.append(
            html.Div([
                html.H3("Related Keywords Trend Comparison", style={'fontSize': '18px', 'fontWeight': '600', 'color': '#1E293B', 'marginBottom': '16px'}),
                dcc.Graph(figure=fig_related, style={'height': '400px'})
            ], style={'backgroundColor': '#FFFFFF', 'padding': '24px', 'borderRadius': '12px', 'border': '1px solid #E2E8F0', 'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)', 'marginBottom': '24px'})
        )
    
    # 3. Trend intensity heatmap
    if data['time_periods']:
        heatmap_data = []
        for period, period_data in data['time_periods'].items():
            if period_data:
                df = pd.DataFrame(period_data)
                avg_value = df['value'].mean()
                max_value = df['value'].max()
                heatmap_data.append({
                    'period': period.replace('_', ' ').title(),
                    'avg_interest': avg_value,
                    'peak_interest': max_value
                })
        
        if heatmap_data:
            heatmap_df = pd.DataFrame(heatmap_data)
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=[heatmap_df['avg_interest'], heatmap_df['peak_interest']],
                x=heatmap_df['period'],
                y=['Average Interest', 'Peak Interest'],
                colorscale='Viridis',
                text=[[f"{val:.1f}" for val in heatmap_df['avg_interest']], 
                      [f"{val:.1f}" for val in heatmap_df['peak_interest']]],
                texttemplate="%{text}",
                textfont={"size": 12},
                hoverongaps=False
            ))
            
            fig_heatmap.update_layout(
                title=f"Interest Intensity Across Time Periods: {keyword.title()}",
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1E293B')
            )
            
            visualizations.append(
                html.Div([
                    html.H3("Interest Intensity Heatmap", style={'fontSize': '18px', 'fontWeight': '600', 'color': '#1E293B', 'marginBottom': '16px'}),
                    dcc.Graph(figure=fig_heatmap, style={'height': '300px'})
                ], style={'backgroundColor': '#FFFFFF', 'padding': '24px', 'borderRadius': '12px', 'border': '1px solid #E2E8F0', 'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)', 'marginBottom': '24px'})
            )
    
    return html.Div(visualizations)

def generate_insights_report(data):
    """Generate insights from comprehensive trend data"""
    if not data:
        return ""
    
    keyword = data['keyword']
    insights = []
    
    # Analyze trends across time periods
    trend_analysis = {}
    for period, period_data in data['time_periods'].items():
        if period_data:
            df = pd.DataFrame(period_data)
            trend_analysis[period] = {
                'avg_interest': df['value'].mean(),
                'peak_interest': df['value'].max(),
                'volatility': df['value'].std(),
                'data_points': len(df)
            }
    
    # Generate insights
    insights.append(f"# Comprehensive Trend Analysis: {keyword.title()}\n")
    insights.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    insights.append(f"**Keyword:** {keyword}\n\n")
    
    insights.append("## Time Period Analysis\n")
    for period, analysis in trend_analysis.items():
        period_name = period.replace('_', ' ').title()
        insights.append(f"### {period_name}")
        insights.append(f"- Average Interest: {analysis['avg_interest']:.1f}")
        insights.append(f"- Peak Interest: {analysis['peak_interest']:.1f}")
        insights.append(f"- Volatility: {analysis['volatility']:.1f}")
        insights.append(f"- Data Points: {analysis['data_points']}\n")
    
    # Related keywords analysis
    if data['related_keywords']:
        insights.append("## Related Keywords Performance\n")
        for related_kw, periods_data in data['related_keywords'].items():
            insights.append(f"### {related_kw}")
            for period, kw_data in periods_data.items():
                if kw_data:
                    df = pd.DataFrame(kw_data)
                    avg_val = df['value'].mean()
                    insights.append(f"- {period.replace('_', ' ').title()}: {avg_val:.1f} avg interest")
            insights.append("")
    
    # Market insights
    insights.append("## Key Market Insights\n")
    
    # Find best performing time period
    if trend_analysis:
        best_period = max(trend_analysis.keys(), key=lambda x: trend_analysis[x]['avg_interest'])
        best_period_name = best_period.replace('_', ' ').title()
        insights.append(f"- **Strongest Performance**: {best_period_name} period with {trend_analysis[best_period]['avg_interest']:.1f} average interest")
        
        # Volatility analysis
        most_volatile = max(trend_analysis.keys(), key=lambda x: trend_analysis[x]['volatility'])
        least_volatile = min(trend_analysis.keys(), key=lambda x: trend_analysis[x]['volatility'])
        insights.append(f"- **Most Volatile**: {most_volatile.replace('_', ' ').title()} period")
        insights.append(f"- **Most Stable**: {least_volatile.replace('_', ' ').title()} period")
    
    # Regional insights
    if data['regional_data']:
        region_df = pd.DataFrame(data['regional_data'])
        top_region = region_df.loc[region_df['value'].idxmax(), 'region']
        insights.append(f"- **Top Performing Region**: {top_region}")
    
    insights.append("\n## Recommendations\n")
    insights.append("Based on the comprehensive analysis:")
    insights.append("1. Focus marketing efforts during peak interest periods")
    insights.append("2. Consider seasonal patterns for inventory planning")
    insights.append("3. Explore related keywords for content strategy")
    insights.append("4. Target high-performing regions for campaigns")
    
    return "\n".join(insights)

# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Color scheme based on the template
colors = {
    'primary': '#6366F1',      # Indigo
    'secondary': '#8B5CF6',    # Purple  
    'success': '#10B981',      # Green
    'warning': '#F59E0B',      # Amber
    'danger': '#EF4444',       # Red
    'info': '#06B6D4',         # Cyan
    'light': '#F8FAFC',        # Light gray
    'dark': '#1E293B',         # Dark slate
    'text_primary': '#1E293B',
    'text_secondary': '#64748B',
    'border': '#E2E8F0',
    'bg_card': '#FFFFFF',
    'bg_main': '#F8FAFC'
}

# Custom styles
custom_styles = {
    'main_container': {
        'backgroundColor': colors['bg_main'],
        'minHeight': '100vh',
        'fontFamily': "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
        'margin': '0',
        'padding': '0'
    },
    'sidebar': {
        'width': '280px',
        'height': '100vh',
        'backgroundColor': colors['bg_card'],
        'position': 'fixed',
        'left': '0',
        'top': '0',
        'borderRight': f'1px solid {colors["border"]}',
        'padding': '0',
        'zIndex': '1000',
        'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
    },
    'sidebar_header': {
        'padding': '24px',
        'borderBottom': f'1px solid {colors["border"]}'
    },
    'logo': {
        'fontSize': '24px',
        'fontWeight': '700',
        'color': colors['primary'],
        'margin': '0'
    },
    'sidebar_nav': {
        'padding': '16px 0'
    },
    'nav_item': {
        'display': 'block',
        'padding': '12px 24px',
        'color': colors['text_secondary'],
        'textDecoration': 'none',
        'fontSize': '14px',
        'fontWeight': '500',
        'borderLeft': '3px solid transparent',
        'transition': 'all 0.2s ease',
        'cursor': 'pointer'
    },
    'nav_item_active': {
        'color': colors['primary'],
        'backgroundColor': '#F0F0FF',
        'borderLeft': f'3px solid {colors["primary"]}'
    },
    'main_content': {
        'marginLeft': '280px',
        'padding': '24px',
        'minHeight': '100vh'
    },
    'header': {
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'marginBottom': '32px',
        'padding': '0'
    },
    'page_title': {
        'fontSize': '28px',
        'fontWeight': '700',
        'color': colors['text_primary'],
        'margin': '0'
    },
    'search_container': {
        'display': 'flex',
        'gap': '12px',
        'alignItems': 'center'
    },
    'search_input': {
        'padding': '12px 16px',
        'border': f'1px solid {colors["border"]}',
        'borderRadius': '8px',
        'fontSize': '14px',
        'minWidth': '300px',
        'outline': 'none',
        'transition': 'border-color 0.2s ease'
    },
    'search_button': {
        'backgroundColor': colors['primary'],
        'color': 'white',
        'border': 'none',
        'borderRadius': '8px',
        'padding': '12px 24px',
        'cursor': 'pointer',
        'fontSize': '14px',
        'fontWeight': '600',
        'transition': 'all 0.2s ease'
    },
    'stats_grid': {
        'display': 'grid',
        'gridTemplateColumns': 'repeat(4, 1fr)',
        'gap': '24px',
        'marginBottom': '32px'
    },
    'stat_card': {
        'backgroundColor': colors['bg_card'],
        'padding': '24px',
        'borderRadius': '12px',
        'border': f'1px solid {colors["border"]}',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    },
    'stat_label': {
        'fontSize': '14px',
        'color': colors['text_secondary'],
        'fontWeight': '500',
        'marginBottom': '8px'
    },
    'stat_value': {
        'fontSize': '32px',
        'fontWeight': '700',
        'color': colors['text_primary'],
        'marginBottom': '4px'
    },
    'stat_change': {
        'fontSize': '14px',
        'fontWeight': '500'
    },
    'charts_grid': {
        'display': 'grid',
        'gridTemplateColumns': '2fr 1fr',
        'gap': '24px',
        'marginBottom': '32px'
    },
    'chart_card': {
        'backgroundColor': colors['bg_card'],
        'padding': '24px',
        'borderRadius': '12px',
        'border': f'1px solid {colors["border"]}',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    },
    'chart_title': {
        'fontSize': '18px',
        'fontWeight': '600',
        'color': colors['text_primary'],
        'marginBottom': '16px'
    },
    'loading_container': {
        'display': 'flex',
        'flexDirection': 'column',
        'alignItems': 'center',
        'justifyContent': 'center',
        'height': '300px',
        'color': colors['text_secondary']
    },
    'markdown_report': {
        'backgroundColor': colors['bg_card'],
        'padding': '40px',
        'borderRadius': '12px',
        'border': f'1px solid {colors["border"]}',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        'lineHeight': '1.6',
        'color': colors['text_primary']
    }
}

# Layout
app.layout = html.Div([
    # Store components for data
    dcc.Store(id='current-keyword-data'),
    dcc.Store(id='current-page', data='overview'),
    dcc.Store(id='fashion-report-data'),
    
    # Sidebar
    html.Div([
        # Sidebar Header
        html.Div([
            html.H1("Claire", style=custom_styles['logo'])
        ], style=custom_styles['sidebar_header']),
        
        # Navigation
        html.Nav([
            html.A("Overview", id='nav-overview', n_clicks=0, style={**custom_styles['nav_item'], **custom_styles['nav_item_active']}),
            html.A("Trends", id='nav-trends', n_clicks=0, style=custom_styles['nav_item']),
            html.A("Analytics", id='nav-analytics', n_clicks=0, style=custom_styles['nav_item']),
            html.A("Reports", id='nav-reports', n_clicks=0, style=custom_styles['nav_item']),
            html.A("Settings", id='nav-settings', n_clicks=0, style=custom_styles['nav_item'])
        ], style=custom_styles['sidebar_nav'])
    ], style=custom_styles['sidebar']),
    
    # Main Content
    html.Div(id='main-content', style=custom_styles['main_content'])
], style=custom_styles['main_container'])

# Page creation functions
def create_placeholder_page(page_name):
    if page_name == 'Reports':
        return create_comprehensive_reports_page()
    else:
        return html.Div([
            html.H1(f"{page_name} Page", style=custom_styles['page_title']),
            html.Div(f"This is the {page_name} page. Content coming soon!", style={
                'marginTop': '40px',
                'fontSize': '16px',
                'color': colors['text_secondary']
            })
        ])

def create_overview_page():
    return html.Div([
        # Header
        html.Div([
            html.H1("Fashion Trend Analysis", style=custom_styles['page_title']),
            html.Div([
                dcc.Input(
                    id='keyword-input',
                    type='text',
                    placeholder='Search fashion trends...',
                    style=custom_styles['search_input']
                ),
                html.Button(
                    "Analyze",
                    id='search-button',
                    style=custom_styles['search_button']
                )
            ], style=custom_styles['search_container'])
        ], style=custom_styles['header']),
        
        # Loading indicator
        html.Div([
            html.Div("Loading trends data...", style={'fontSize': '18px', 'marginBottom': '12px'}),
            html.Div("Fetching fresh data from Google Trends...", 
                    style={'fontSize': '14px', 'color': colors['text_secondary']})
        ], id='loading-indicator', style={**custom_styles['loading_container'], 'display': 'none'}),

        # Current keyword display
        html.Div(id='current-keyword-display', style={'marginBottom': '24px'}),
        
        # Stats Grid
        html.Div(id='stats-grid', children=[
            html.Div([
                html.Div("Total Searches", style=custom_styles['stat_label']),
                html.Div("--", id='total-searches', style=custom_styles['stat_value']),
                html.Div("", id='searches-change', style=custom_styles['stat_change'])
            ], style=custom_styles['stat_card']),
            
            html.Div([
                html.Div("Peak Interest", style=custom_styles['stat_label']),
                html.Div("--", id='peak-interest', style=custom_styles['stat_value']),
                html.Div("", id='peak-change', style=custom_styles['stat_change'])
            ], style=custom_styles['stat_card']),
            
            html.Div([
                html.Div("Active Regions", style=custom_styles['stat_label']),
                html.Div("--", id='active-regions', style=custom_styles['stat_value']),
                html.Div("", id='regions-change', style=custom_styles['stat_change'])
            ], style=custom_styles['stat_card']),
            
            html.Div([
                html.Div("Trend Score", style=custom_styles['stat_label']),
                html.Div("--", id='trend-score', style=custom_styles['stat_value']),
                html.Div("", id='score-change', style=custom_styles['stat_change'])
            ], style=custom_styles['stat_card'])
        ], style=custom_styles['stats_grid']),

        # Charts Container
        html.Div(id='charts-container', children=[
            # Main charts grid
            html.Div([
                # Regional Map
                html.Div([
                    html.H3("Regional Interest Distribution", style=custom_styles['chart_title']),
                    dcc.Graph(id='india-map', style={'height': '400px'})
                ], style=custom_styles['chart_card']),

                # Top Regions
                html.Div([
                    html.H3("Top Performing Regions", style=custom_styles['chart_title']),
                    dcc.Graph(id='top-regions-bar', style={'height': '400px'})
                ], style=custom_styles['chart_card'])
            ], style=custom_styles['charts_grid']),

            # Time series chart
            html.Div([
                html.H3("Trend Analysis Over Time", style=custom_styles['chart_title']),
                dcc.Graph(id='time-series', style={'height': '400px'})
            ], style=custom_styles['chart_card']),

            # Related queries
            html.Div([
                html.H3("Related Fashion Trends", style=custom_styles['chart_title']),
                html.Div(id='related-queries-table', style={'minHeight': '200px'})
            ], style={**custom_styles['chart_card'], 'marginTop': '24px'})
        ], style={'display': 'none'})
    ])

def create_trends_page():
    return html.Div([
        # Header
        html.Div([
            html.H1("State-wise Fashion Trends & Blog Analysis", style=custom_styles['page_title']),
            html.Div([
                dcc.Input(
                    id='fashion-keyword-input',
                    type='text',
                    placeholder='Enter fashion item (e.g., saree, dress, jeans)...',
                    style=custom_styles['search_input']
                ),
                dcc.Dropdown(
                    id='state-selector',
                    options=[
                        {'label': 'All India', 'value': 'IN'},
                        {'label': 'Andhra Pradesh', 'value': 'Andhra Pradesh'},
                        {'label': 'Karnataka', 'value': 'Karnataka'},
                        {'label': 'Kerala', 'value': 'Kerala'},
                        {'label': 'Tamil Nadu', 'value': 'Tamil Nadu'},
                        {'label': 'Telangana', 'value': 'Telangana'},
                        {'label': 'Maharashtra', 'value': 'Maharashtra'},
                        {'label': 'Gujarat', 'value': 'Gujarat'},
                        {'label': 'Delhi', 'value': 'Delhi'},
                        {'label': 'Uttar Pradesh', 'value': 'Uttar Pradesh'},
                        {'label': 'West Bengal', 'value': 'West Bengal'},
                        {'label': 'Rajasthan', 'value': 'Rajasthan'},
                        {'label': 'Punjab', 'value': 'Punjab'},
                        {'label': 'Haryana', 'value': 'Haryana'},
                        {'label': 'Bihar', 'value': 'Bihar'},
                        {'label': 'Odisha', 'value': 'Odisha'}
                    ],
                    value='IN',
                    placeholder='Select State',
                    style={'minWidth': '200px', 'marginRight': '12px'}
                ),
                html.Button(
                    "Analyze State Trends",
                    id='analyze-state-button',
                    style=custom_styles['search_button']
                ),
                html.Button(
                    "Generate Blog Report",
                    id='generate-report-button',
                    style={**custom_styles['search_button'], 'backgroundColor': colors['secondary']}
                )
            ], style=custom_styles['search_container'])
        ], style=custom_styles['header']),
        
        # Instructions
        html.Div([
            html.H3("Features:", style={'color': colors['text_primary'], 'marginBottom': '12px'}),
            html.Ol([
                html.Li("Enter a fashion item you want to analyze"),
                html.Li("Select a specific Indian state or 'All India' for national trends"),
                html.Li("Click 'Analyze State Trends' to see statistical data for that state"),
                html.Li("Click 'Generate Blog Report' to get comprehensive fashion blog analysis")
            ], style={'color': colors['text_secondary'], 'lineHeight': '1.8'})
        ], style={
            'backgroundColor': colors['bg_card'],
            'padding': '24px',
            'borderRadius': '12px',
            'border': f'1px solid {colors["border"]}',
            'marginBottom': '32px'
        }),
        
        # State trends display area
        html.Div(id='state-trends-display', style={'marginBottom': '32px'}),
        
        # Loading indicator for report
        html.Div([
            html.Div("Analyzing fashion blogs...", style={'fontSize': '18px', 'marginBottom': '12px'}),
            html.Div(id='analysis-progress', children="Starting analysis...", 
                    style={'fontSize': '14px', 'color': colors['text_secondary']}),
        ], id='report-loading-indicator', style={**custom_styles['loading_container'], 'display': 'none'}),
        
        # Report display area
        html.Div(id='fashion-report-display', style={'marginTop': '32px'})
    ])

def create_comprehensive_reports_page():
    """Create the enhanced reports page"""
    return html.Div([
        # Header
        html.Div([
            html.H1("Comprehensive Trend Reports", style=custom_styles['page_title']),
            html.Div([
                dcc.Input(
                    id='report-keyword-input',
                    type='text',
                    placeholder='Enter fashion keyword for comprehensive analysis...',
                    style=custom_styles['search_input']
                ),
                html.Button(
                    "Generate Comprehensive Report",
                    id='generate-comprehensive-report-button',
                    style=custom_styles['search_button']
                )
            ], style=custom_styles['search_container'])
        ], style=custom_styles['header']),
        
        # Instructions
        html.Div([
            html.H3("Comprehensive Analysis Features:", style={'color': colors['text_primary'], 'marginBottom': '12px'}),
            html.Ul([
                html.Li("Multi-timeframe analysis (1 day to 12 months)"),
                html.Li("Related keywords discovery and analysis"),
                html.Li("Regional interest patterns"),
                html.Li("Trend comparison across different time periods"),
                html.Li("Seasonal pattern identification"),
                html.Li("Market opportunity insights")
            ], style={'color': colors['text_secondary'], 'lineHeight': '1.8'})
        ], style={
            'backgroundColor': colors['bg_card'],
            'padding': '24px',
            'borderRadius': '12px',
            'border': f'1px solid {colors["border"]}',
            'marginBottom': '32px'
        }),
        
        # Loading indicator
        html.Div([
            html.Div("Analyzing comprehensive trend data...", style={'fontSize': '18px', 'marginBottom': '12px'}),
            html.Div(id='comprehensive-analysis-progress', children="Preparing analysis...", 
                    style={'fontSize': '14px', 'color': colors['text_secondary']}),
        ], id='comprehensive-loading-indicator', style={**custom_styles['loading_container'], 'display': 'none'}),
        
        # Report display area
        html.Div(id='comprehensive-report-display', style={'marginTop': '32px'})
    ])

# Callback to handle navigation
@app.callback(
    [Output('nav-overview', 'style'),
     Output('nav-trends', 'style'),
     Output('nav-analytics', 'style'),
     Output('nav-reports', 'style'),
     Output('nav-settings', 'style'),
     Output('current-page', 'data'),
     Output('main-content', 'children')],
    [Input('nav-overview', 'n_clicks'),
     Input('nav-trends', 'n_clicks'),
     Input('nav-analytics', 'n_clicks'),
     Input('nav-reports', 'n_clicks'),
     Input('nav-settings', 'n_clicks')],
    State('current-page', 'data')
)
def handle_navigation(overview_clicks, trends_clicks, analytics_clicks, reports_clicks, settings_clicks, current_page):
    ctx_triggered = ctx.triggered
    if not ctx_triggered:
        page = 'overview'
    else:
        button_id = ctx_triggered[0]['prop_id'].split('.')[0]
        page = button_id.split('-')[1]
    
    # Reset all nav styles
    nav_styles = [custom_styles['nav_item'] for _ in range(5)]
    
    # Set active style and content
    if page == 'overview':
        nav_styles[0] = {**custom_styles['nav_item'], **custom_styles['nav_item_active']}
        content = create_overview_page()
    elif page == 'trends':
        nav_styles[1] = {**custom_styles['nav_item'], **custom_styles['nav_item_active']}
        content = create_trends_page()
    elif page == 'analytics':
        nav_styles[2] = {**custom_styles['nav_item'], **custom_styles['nav_item_active']}
        content = create_placeholder_page('Analytics')
    elif page == 'reports':
        nav_styles[3] = {**custom_styles['nav_item'], **custom_styles['nav_item_active']}
        content = create_placeholder_page('Reports')
    elif page == 'settings':
        nav_styles[4] = {**custom_styles['nav_item'], **custom_styles['nav_item_active']}
        content = create_placeholder_page('Settings')
    else:
        content = create_overview_page()
    
    return nav_styles[0], nav_styles[1], nav_styles[2], nav_styles[3], nav_styles[4], page, content

# Callback to handle state-wise trends analysis
@app.callback(
    Output('state-trends-display', 'children'),
    Input('analyze-state-button', 'n_clicks'),
    [State('fashion-keyword-input', 'value'),
     State('state-selector', 'value')],
    prevent_initial_call=True
)
def analyze_state_trends(n_clicks, keyword, state):
    if not keyword:
        return html.Div(
            "Please enter a fashion item to analyze.",
            style={'color': colors['danger'], 'fontSize': '16px'}
        )
    
    # Fetch state-wise trends data
    time_data, city_data, state_codes = fetch_state_wise_trends(keyword, state)
    
    if time_data.empty and city_data.empty:
        return html.Div(
            f"No trends data available for '{keyword}' in {state}",
            style={'color': colors['warning'], 'fontSize': '16px'}
        )
    
    # Create visualizations
    charts = []
    
    # Time series chart for state
    if not time_data.empty:
        time_data['date'] = pd.to_datetime(time_data['date'])
        fig_time = px.line(
            time_data, x='date', y='value',
            title=f"Trend Over Time: {keyword.title()} in {state}"
        )
        fig_time.update_traces(line_color=colors['primary'], line_width=3)
        fig_time.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=colors['text_primary'])
        )
        
        charts.append(
            html.Div([
                html.H3(f"Trend Analysis: {keyword.title()} in {state}", style=custom_styles['chart_title']),
                dcc.Graph(figure=fig_time, style={'height': '400px'})
            ], style=custom_styles['chart_card'])
        )
    
    # City-wise bar chart
    if not city_data.empty:
        top_cities = city_data.nlargest(10, 'value')
        fig_cities = px.bar(
            top_cities, x='value', y='city', orientation='h',
            title=f"Top Cities for {keyword.title()} in {state}"
        )
        fig_cities.update_traces(marker_color=colors['secondary'])
        fig_cities.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=colors['text_primary'])
        )
        
        charts.append(
            html.Div([
                html.H3(f"City-wise Interest: {keyword.title()}", style=custom_styles['chart_title']),
                dcc.Graph(figure=fig_cities, style={'height': '400px'})
            ], style=custom_styles['chart_card'])
        )
    
    return html.Div(charts)

# Callback to handle fashion report generation
@app.callback(
    [Output('fashion-report-display', 'children'),
     Output('report-loading-indicator', 'style'),
     Output('analysis-progress', 'children')], 
    Input('generate-report-button', 'n_clicks'),
    State('fashion-keyword-input', 'value'),  
    prevent_initial_call=True
)
def generate_fashion_report(n_clicks, keyword):
    if not keyword:
        return html.Div(
            "Please enter a fashion item.",
            style={'color': colors['danger'], 'fontSize': '16px', 'marginTop': '20px'}
        ), {'display': 'none'}, ""
    
    # Show loading
    loading_style = custom_styles['loading_container']

    try:
        # Initialize analyzer
        analyzer = AutomatedFashionAnalyzer(SERPER_API_KEY)
        
        # Analyze blogs
        blog_data = analyzer.analyze_all_blogs(keyword)
        
        if not blog_data:
            return html.Div(
                "No relevant fashion blogs found for this keyword. Try another fashion item.",
                style={'color': colors['danger'], 'fontSize': '16px', 'marginTop': '20px'}
            ), {'display': 'none'}, ""
        
        # Generate report
        report_markdown = analyzer.generate_comprehensive_report(keyword, blog_data)
        
        if not report_markdown:
            return html.Div(
                "Failed to generate report. Please try again.",
                style={'color': colors['danger'], 'fontSize': '16px', 'marginTop': '20px'}
            ), {'display': 'none'}, ""
        
        # Create beautiful report display
        report_display = html.Div([
            html.Div([
                html.Div([
                    html.Div(f"Analysis completed for: {keyword.title()}", style={
                        'fontSize': '14px',
                        'color': colors['text_secondary']
                    })
                ], style={
                    'backgroundColor': colors['bg_card'],
                    'padding': '20px',
                    'borderRadius': '8px',
                    'border': f'1px solid {colors["success"]}',
                    'marginBottom': '24px'
                }),
                
                dcc.Markdown(
                    report_markdown,
                    style={
                        **custom_styles['markdown_report'],
                        'fontSize': '16px',
                        'maxWidth': '100%',
                        'overflowX': 'auto'
                    },
                    dangerously_allow_html=True
                ),

                
                # Download button
                html.Div([
                    html.Button(
                        "Download Report as Markdown",
                        id='download-report-button',
                        style={
                            **custom_styles['search_button'],
                            'backgroundColor': colors['secondary'],
                            'marginTop': '24px'
                        }
                    ),
                    dcc.Download(id='download-report')
                ], style={'textAlign': 'center'})
            ])
        ], style={'animation': 'fadeIn 0.5s ease-in'})
        
        # Store report data for download
        report_display.children.append(
            dcc.Store(id='report-markdown-data', data=report_markdown)
        )
        
        return report_display, {'display': 'none'}, ""
        
    except Exception as e:
        return html.Div(
            f"Error generating report: {str(e)}",
            style={'color': colors['danger'], 'fontSize': '16px', 'marginTop': '20px'}
        ), {'display': 'none'}, ""

# Callback for comprehensive report generation
@app.callback(
    [Output('comprehensive-report-display', 'children'),
     Output('comprehensive-loading-indicator', 'style'),
     Output('comprehensive-analysis-progress', 'children')],
    Input('generate-comprehensive-report-button', 'n_clicks'),
    State('report-keyword-input', 'value'),
    prevent_initial_call=True
)
def generate_comprehensive_report(n_clicks, keyword):
    if not keyword:
        return html.Div(
            "Please enter a fashion keyword to analyze.",
            style={'color': colors['danger'], 'fontSize': '16px'}
        ), {'display': 'none'}, ""
    
    # Show loading
    loading_style = custom_styles['loading_container']
    
    try:
        # Fetch comprehensive data
        comprehensive_data = fetch_comprehensive_trend_data(keyword)
        
        if not comprehensive_data['time_periods']:
            return html.Div(
                "No trend data available for this keyword. Please try another keyword.",
                style={'color': colors['warning'], 'fontSize': '16px'}
            ), {'display': 'none'}, ""
        
        # Create visualizations
        visualizations = create_comprehensive_report_visualizations(comprehensive_data)
        
        # Generate insights
        insights_markdown = generate_insights_report(comprehensive_data)
        
        # Create comprehensive report display
        report_display = html.Div([
            # Summary stats
            html.Div([
                html.H3(f"Comprehensive Analysis: {keyword.title()}", style=custom_styles['chart_title']),
                html.Div([
                    html.Div([
                        html.Div("Time Periods Analyzed", style=custom_styles['stat_label']),
                        html.Div(str(len([p for p in comprehensive_data['time_periods'] if comprehensive_data['time_periods'][p]])), 
                                style=custom_styles['stat_value'])
                    ], style=custom_styles['stat_card']),
                    html.Div([
                        html.Div("Related Keywords Found", style=custom_styles['stat_label']),
                        html.Div(str(len(comprehensive_data['related_keywords'])), 
                                style=custom_styles['stat_value'])
                    ], style=custom_styles['stat_card']),
                    html.Div([
                        html.Div("Regions Analyzed", style=custom_styles['stat_label']),
                        html.Div(str(len(comprehensive_data['regional_data'])), 
                                style=custom_styles['stat_value'])
                    ], style=custom_styles['stat_card'])
                ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '24px', 'marginBottom': '32px'})
            ], style=custom_styles['chart_card']),
            
            # Visualizations
            visualizations,
            
            # Insights report
            html.Div([
                html.H3("Detailed Insights & Recommendations", style=custom_styles['chart_title']),
                dcc.Markdown(
                    insights_markdown,
                    style={
                        'fontSize': '16px',
                        'lineHeight': '1.6',
                        'color': colors['text_primary']
                    }
                )
            ], style=custom_styles['markdown_report'])
        ])
        
        return report_display, {'display': 'none'}, ""
        
    except Exception as e:
        return html.Div(
            f"Error generating comprehensive report: {str(e)}",
            style={'color': colors['danger'], 'fontSize': '16px'}
        ), {'display': 'none'}, ""

# Callback for downloading report
@app.callback(
    Output('download-report', 'data'),
    Input('download-report-button', 'n_clicks'),
    State('report-markdown-data', 'data'),
    State('fashion-keyword-input', 'value'),
    prevent_initial_call=True
)
def download_report(n_clicks, report_data, keyword):
    if report_data:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"fashion_report_{keyword.lower().replace(' ', '_')}_{timestamp}.md"
        return dict(content=report_data, filename=filename)
    return None

# Main callback to handle search (from original code)
@app.callback(
    [Output('current-keyword-data', 'data'),
     Output('loading-indicator', 'style'),
     Output('charts-container', 'style'),
     Output('current-keyword-display', 'children')],
    [Input('search-button', 'n_clicks'),
     Input({'type': 'related-query-click', 'index': ALL}, 'n_clicks')],
    [State('keyword-input', 'value'),
     State('current-keyword-data', 'data')],
    prevent_initial_call=True
)
def handle_search(search_clicks, related_clicks, keyword_input, current_data):
    # Determine which input triggered the callback
    ctx_triggered = ctx.triggered[0]
    
    keyword_to_search = None
    
    if 'search-button' in ctx_triggered['prop_id'] and keyword_input:
        keyword_to_search = keyword_input.strip().lower()
    elif 'related-query-click' in ctx_triggered['prop_id'] and any(related_clicks):
        # Find which related query was clicked
        button_id = json.loads(ctx_triggered['prop_id'].split('.')[0])
        keyword_to_search = button_id['index'].strip().lower()
    
    if not keyword_to_search:
        return current_data or {}, {'display': 'none'}, {'display': 'none'}, ""
    
    # Show loading
    loading_style = custom_styles['loading_container']
    charts_style = {'display': 'none'}
    
    # Fetch data
    time_df, region_df, related_df = fetch_single_keyword_data(keyword_to_search)
    
    # Prepare data for storage
    data = {
        'keyword': keyword_to_search,
        'time_data': time_df.to_dict('records') if not time_df.empty else [],
        'region_data': region_df.to_dict('records') if not region_df.empty else [],
        'related_data': related_df.to_dict('records') if not related_df.empty else [],
        'timestamp': datetime.now().isoformat()
    }
    
    # Hide loading, show charts
    loading_style = {'display': 'none'}
    charts_style = {'display': 'block'}
    
    # Current keyword display
    keyword_display = html.Div([
        html.Div(f"Analyzing: {keyword_to_search.title()}", style={
            'color': colors['text_primary'],
            'fontSize': '16px',
            'fontWeight': '600',
            'padding': '16px 24px',
            'backgroundColor': colors['bg_card'],
            'borderRadius': '8px',
            'border': f'1px solid {colors["border"]}',
            'marginBottom': '24px'
        })
    ])
    
    return data, loading_style, charts_style, keyword_display

# Callback to update stats
@app.callback(
    [Output('total-searches', 'children'),
     Output('peak-interest', 'children'),
     Output('active-regions', 'children'),
     Output('trend-score', 'children'),
     Output('searches-change', 'children'),
     Output('peak-change', 'children'),
     Output('regions-change', 'children'),
     Output('score-change', 'children')],
    Input('current-keyword-data', 'data')
)
def update_stats(data):
    if not data:
        return "--", "--", "--", "--", "", "", "", ""
    
    time_df = pd.DataFrame(data['time_data'])
    region_df = pd.DataFrame(data['region_data'])
    
    # Calculate stats
    total_searches = len(time_df) if not time_df.empty else 0
    peak_interest = int(time_df['value'].max()) if not time_df.empty else 0
    active_regions = len(region_df[region_df['value'] > 0]) if not region_df.empty else 0
    trend_score = int(time_df['value'].mean()) if not time_df.empty else 0
    
    # Mock percentage changes (in real app, compare with previous data)
    changes = ["+12.5%", "+8.2%", "+15.3%", "+6.7%"]
    change_colors = [colors['success'], colors['success'], colors['success'], colors['success']]
    
    change_styles = [{'color': color} for color in change_colors]
    
    return (f"{total_searches:,}", f"{peak_interest}", f"{active_regions}", f"{trend_score}",
            html.Span(changes[0], style=change_styles[0]),
            html.Span(changes[1], style=change_styles[1]),
            html.Span(changes[2], style=change_styles[2]),
            html.Span(changes[3], style=change_styles[3]))

# Callback to update all charts
@app.callback(
    [Output("india-map", "figure"),
     Output("time-series", "figure"),
     Output("top-regions-bar", "figure"),
     Output("related-queries-table", "children")],
    Input('current-keyword-data', 'data')
)
def update_charts(data):
    if not data:
        empty_fig = go.Figure().add_annotation(
            text="Enter a fashion keyword to start analyzing trends", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, 
            font=dict(size=16, color=colors['text_secondary'])
        )
        empty_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis={'visible': False}, yaxis={'visible': False},
            margin=dict(l=0, r=0, t=0, b=0)
        )
        return empty_fig, empty_fig, empty_fig, ""
    
    # Convert data back to DataFrames
    time_df = pd.DataFrame(data['time_data'])
    region_df = pd.DataFrame(data['region_data'])
    related_df = pd.DataFrame(data['related_data'])
    keyword = data['keyword']
    
    # 1. CHOROPLETH MAP
    if not region_df.empty and geojson_data:
        fig_map = px.choropleth(
            region_df, geojson=geojson_data, featureidkey="properties.ST_NM",
            locations="region", color="value",
            color_continuous_scale="Viridis", hover_name="region", 
            hover_data={'value': ':.0f'}
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(
            font=dict(color=colors['text_primary'], size=12),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    else:
        fig_map = go.Figure().add_annotation(
            text="No regional data available", x=0.5, y=0.5,
            font=dict(color=colors['text_secondary'])
        )
        fig_map.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            margin=dict(l=0, r=0, t=0, b=0)
        )

    # 2. TIME SERIES
    if not time_df.empty:
        time_df['date'] = pd.to_datetime(time_df['date'])
        fig_time = px.line(
            time_df, x='date', y='value',
            line_shape='spline'
        )
        fig_time.update_traces(
            line_color=colors['primary'], 
            line_width=3,
            fill='tonexty',
            fillcolor=f'rgba(99, 102, 241, 0.1)'
        )
        fig_time.update_layout(
            font=dict(color=colors['text_primary'], size=12),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor=colors['border']),
            yaxis=dict(showgrid=True, gridcolor=colors['border'])
        )
    else:
        fig_time = go.Figure().add_annotation(
            text="No time series data available", x=0.5, y=0.5,
            font=dict(color=colors['text_secondary'])
        )
        fig_time.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            margin=dict(l=0, r=0, t=0, b=0)
        )

    # 3. BAR CHART
    if not region_df.empty:
        top_regions = region_df.nlargest(10, 'value')
        fig_bar = px.bar(
            top_regions, x='value', y='region', orientation='h'
        )
        fig_bar.update_traces(marker_color=colors['secondary'])
        fig_bar.update_layout(
            font=dict(color=colors['text_primary'], size=12),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor=colors['border']),
            yaxis=dict(showgrid=False)
        )
    else:
        fig_bar = go.Figure().add_annotation(
            text="No regional data available", x=0.5, y=0.5,
            font=dict(color=colors['text_secondary'])
        )
        fig_bar.update_layout(
            xaxis={'visible': False}, yaxis={'visible': False},
            margin=dict(l=0, r=0, t=0, b=0)
        )

    # 4. RELATED QUERIES TABLE
    if not related_df.empty:
        table_rows = []
        for i, (_, row) in enumerate(related_df.iterrows()):
            row_cells = []
            for col in related_df.columns:
                if col == 'query':
                    cell_content = html.Button(
                        str(row[col]), 
                        id={'type': 'related-query-click', 'index': str(row[col])},
                        style={
                            'background': 'none', 
                            'border': 'none', 
                            'color': colors['primary'],
                            'textDecoration': 'underline', 
                            'cursor': 'pointer', 
                            'fontSize': '14px',
                            'fontWeight': '500', 
                            'padding': '8px'
                        }
                    )
                else:
                    cell_content = str(row[col])
                
                row_cells.append(html.Td(
                    cell_content, 
                    style={
                        'padding': '12px', 
                        'borderBottom': f'1px solid {colors["border"]}',
                        'fontSize': '14px'
                    }
                ))
            
            bg_color = colors['light'] if i % 2 == 0 else 'white'
            table_rows.append(html.Tr(row_cells, style={'backgroundColor': bg_color}))
        
        header_cells = []
        for col in related_df.columns:
            header_cells.append(html.Th(
                col.replace('_', ' ').title(), 
                style={
                    'backgroundColor': colors['primary'], 
                    'color': 'white', 
                    'padding': '16px 12px',
                    'fontWeight': '600', 
                    'textAlign': 'left',
                    'fontSize': '14px'
                }
            ))
        
        table_html = html.Table([
            html.Thead([html.Tr(header_cells)]),
            html.Tbody(table_rows)
        ], style={
            'width': '100%', 
            'borderCollapse': 'collapse', 
            'borderRadius': '8px', 
            'overflow': 'hidden',
            'border': f'1px solid {colors["border"]}'
        })
    else:
        table_html = html.Div(
            "No related queries available", 
            style={
                'textAlign': 'center', 
                'padding': '40px', 
                'color': colors['text_secondary'],
                'fontSize': '14px'
            }
        )

    return fig_map, fig_time, fig_bar, table_html

# Enhanced CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Claire - Fashion Trend Analysis</title>
        {%favicon%}
        {%css%}
        <style>
            body { margin: 0; padding: 0; }
            input:focus { 
                outline: none; 
                border-color: #6366F1; 
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); 
            }
            button:hover { 
                transform: translateY(-1px); 
                box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
            }
            .nav-item:hover {
                background-color: #F8FAFC !important;
            }
            button[id*="related-query-click"]:hover { 
                background-color: rgba(99, 102, 241, 0.1) !important; 
                color: #4F46E5 !important; 
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            /* Markdown styling */
            .markdown-report h1 { color: #1E293B; margin-top: 32px; }
            .markdown-report h2 { color: #334155; margin-top: 24px; }
            .markdown-report h3 { color: #475569; margin-top: 20px; }
            .markdown-report ul { padding-left: 24px; }
            .markdown-report li { margin: 8px 0; }
            .markdown-report p { margin: 16px 0; }
            .markdown-report strong { color: #1E293B; }
            .markdown-report code { 
                background: #F1F5F9; 
                padding: 2px 6px; 
                border-radius: 4px; 
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))

