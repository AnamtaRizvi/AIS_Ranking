#!/usr/bin/env python3
"""
Script to fetch papers from OpenAlex for specified journals.
"""

import requests
import json
import os
import time
from typing import Dict, List, Any, Optional
from openai import OpenAI

# Journal configuration
JOURNALS = {
    "AISEJ": {
        "name": "AIS Educator Journal",
        "issn_online": "1935-8156",
    },
    "IJAIS": {
        "name": "International Journal of Accounting Information Systems",
        "issn_online": "1467-0895",
    },
    "IJDAR": {
        "name": "International Journal on Document Analysis and Recognition",
        "issn_online": "1433-2825",
    },
    "ISAFM": {
        "name": "Intelligent Systems in Accounting, Finance and Management",
        "issn_online": "2160-0074",
    },
    "JETA": {
        "name": "Journal of Emerging Technologies in Accounting",
        "issn_online": "1558-7940",
    },
    "JIS": {
        "name": "Journal of Information Systems",
        "issn_online": "1558-7959",
    },
}

OPENALEX_BASE_URL = "https://api.openalex.org"

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
OPENAI_MODEL = "gpt-4o-mini"  # Using gpt-4o-mini for cost efficiency, can change to gpt-4 or gpt-3.5-turbo

# Classification categories
PAPER_CATEGORIES = [
    "Accounting & Financial AI",
    "Business Intelligence & Decision Support",
    "Information Systems & Applied Analytics",
    "Engineering & Industrial AI",
    "Core AI & Data Science Methods"
]


def get_source_by_issn(issn: str) -> Dict[str, Any]:
    """
    Get source (journal) information by ISSN from OpenAlex.
    """
    url = f"{OPENALEX_BASE_URL}/sources/issn:{issn}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching source for ISSN {issn}: {e}")
        return None


def fetch_papers_for_source(source_id: str, per_page: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch papers (works) for a given source ID.
    """
    all_papers = []
    page = 1
    has_more = True
    
    while has_more:
        url = f"{OPENALEX_BASE_URL}/works"
        params = {
            "filter": f"primary_location.source.id:{source_id}",
            "per_page": per_page,
            "page": page,
            "sort": "publication_date:desc"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            papers = data.get("results", [])
            all_papers.extend(papers)
            
            # Check if there are more pages
            has_more = len(papers) == per_page
            page += 1
            
            print(f"Fetched {len(papers)} papers (page {page - 1}), total so far: {len(all_papers)}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching papers for source {source_id}: {e}")
            break
    
    return all_papers


def fetch_all_journal_papers() -> Dict[str, Dict[str, Any]]:
    """
    Fetch papers for all configured journals.
    """
    results = {}
    
    for journal_code, journal_info in JOURNALS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {journal_info['name']} ({journal_code})")
        print(f"ISSN: {journal_info['issn_online']}")
        print(f"{'='*60}")
        
        # First, get the source (journal) by ISSN
        source = get_source_by_issn(journal_info['issn_online'])
        
        if source:
            source_id = source.get('id', '').split('/')[-1]  # Extract ID from URL
            source_name = source.get('display_name', journal_info['name'])
            
            print(f"Found source: {source_name} (ID: {source_id})")
            
            # Fetch papers for this source
            papers = fetch_papers_for_source(source_id)
            
            results[journal_code] = {
                "name": source_name,
                "issn": journal_info['issn_online'],
                "source_id": source_id,
                "paper_count": len(papers),
                "papers": papers
            }
            
            print(f"\n✓ Total papers fetched: {len(papers)}")
        else:
            print(f"✗ Could not find source for ISSN {journal_info['issn_online']}")
            results[journal_code] = {
                "name": journal_info['name'],
                "issn": journal_info['issn_online'],
                "source_id": None,
                "paper_count": 0,
                "papers": []
            }
    
    return results


def extract_organizations_from_papers(results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Extract organizations from all papers and count papers per organization and per category.
    Each paper contributes +1 to each unique organization that has authors on it.
    Also tracks category counts per organization.
    """
    organizations = {}
    
    # Iterate through all journals
    for journal_code, journal_data in results.items():
        papers = journal_data.get('papers', [])
        
        # Iterate through all papers in this journal
        for paper in papers:
            authorships = paper.get('authorships', [])
            
            # Get paper classification if available
            classification = paper.get('classification', {})
            paper_category = classification.get('label', '') if classification else ''
            
            # Collect unique institution IDs for this paper
            paper_institutions = set()
            
            for authorship in authorships:
                institutions = authorship.get('institutions', [])
                
                for institution in institutions:
                    if institution and institution.get('id'):
                        inst_id = institution['id']
                        paper_institutions.add(inst_id)
            
            # Each unique institution on this paper gets +1 count
            for inst_id in paper_institutions:
                if inst_id not in organizations:
                    # Get institution data from the first occurrence
                    # Find the institution data from any authorship
                    inst_data = None
                    for authorship in authorships:
                        institutions = authorship.get('institutions', [])
                        for inst in institutions:
                            if inst and inst.get('id') == inst_id:
                                inst_data = inst
                                break
                        if inst_data:
                            break
                    
                    if inst_data:
                        # Initialize category counts
                        category_counts = {category: 0 for category in PAPER_CATEGORIES}
                        organizations[inst_id] = {
                            "name": inst_data.get('display_name', 'Unknown Institution'),
                            "country": inst_data.get('country_code', 'N/A'),
                            "paper_count": 0,
                            "category_counts": category_counts,
                            "openalex_url": inst_id
                        }
                
                # Increment total count for this organization
                organizations[inst_id]["paper_count"] += 1
                
                # Increment category count if paper is classified
                if paper_category and paper_category in organizations[inst_id]["category_counts"]:
                    organizations[inst_id]["category_counts"][paper_category] += 1
    
    return organizations


def rank_organizations(organizations: Dict[str, Dict[str, Any]], top_n: int = 50) -> List[Dict[str, Any]]:
    """
    Rank organizations by paper count and return top N organizations.
    """
    # Convert to list and sort by paper count (descending)
    org_list = list(organizations.values())
    org_list.sort(key=lambda x: x['paper_count'], reverse=True)
    
    # Return top N
    return org_list[:top_n]


def extract_abstract(paper: Dict[str, Any]) -> str:
    """
    Extract abstract from paper. OpenAlex may have abstract_inverted_index or abstract field.
    """
    # Try abstract field first
    if paper.get('abstract'):
        return paper['abstract']
    
    # Try abstract_inverted_index (inverted index format)
    if paper.get('abstract_inverted_index'):
        abstract_dict = paper['abstract_inverted_index']
        # Convert inverted index to text
        words = []
        for word, positions in abstract_dict.items():
            for pos in positions:
                words.append((pos, word))
        words.sort()
        return ' '.join([word for _, word in words])
    
    return ""


def extract_concepts_hint(paper: Dict[str, Any]) -> str:
    """
    Extract OpenAlex concepts/topics as a hint string for classification.
    """
    concepts = paper.get('concepts', [])
    if not concepts:
        return ""
    
    # Get top concepts (sorted by score if available)
    concept_list = []
    for concept in concepts[:10]:  # Top 10 concepts
        concept_name = concept.get('display_name', '')
        score = concept.get('score', 0)
        if concept_name:
            concept_list.append(f"{concept_name} (score: {score:.2f})")
    
    return "; ".join(concept_list) if concept_list else ""


def classify_papers_batch(papers: List[Dict[str, Any]], batch_num: int = 1) -> List[Dict[str, Any]]:
    """
    Classify a batch of up to 30 papers using OpenAI API.
    Returns list of classification results.
    """
    if not OPENAI_CLIENT:
        print("Warning: OpenAI API key not found. Skipping classification.")
        return []
    
    if not papers:
        return []
    
    # Build prompt with classification rules
    prompt = """Classify each paper into exactly ONE label from:
["Accounting & Financial AI","Business Intelligence & Decision Support","Information Systems & Applied Analytics","Engineering & Industrial AI","Core AI & Data Science Methods"]

Use the OpenAlex topic context strongly.
- If it's about accounting/auditing/finance + ML/AI → Accounting & Financial AI
- If it's about dashboards/decision support/BI/MIS for org decisions → Business Intelligence & Decision Support
- If it's about IS adoption, ERP, governance, analytics in org settings → Information Systems & Applied Analytics
- If it's about manufacturing/operations/supply chain/industrial systems + AI → Engineering & Industrial AI
- If it's mostly algorithms/models/methods with little domain focus → Core AI & Data Science Methods

Return JSON array only, one object per paper:
[{"label":"...", "confidence":0-1, "why":"<=12 words"}, ...]

Papers to classify:
"""
    
    # Add each paper's data
    for i, paper in enumerate(papers, 1):
        title = paper.get('title', 'No title')
        abstract = extract_abstract(paper)
        concepts_hint = extract_concepts_hint(paper)
        
        prompt += f"\nPaper {i}:\n"
        prompt += f"Title: {title}\n"
        prompt += f"Abstract: {abstract}\n"
        prompt += f"OpenAlexHint: {concepts_hint}\n"
        prompt += "---\n"
    
    prompt += "\n\nReturn a JSON array with exactly one object per paper in the same order. Format: [{\"label\":\"...\", \"confidence\":0.0-1.0, \"why\":\"<=12 words\"}, ...]"
    
    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a research paper classifier. You must return a valid JSON array with one classification object per paper. Each object must have 'label', 'confidence' (0-1), and 'why' (max 12 words) fields."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up the response - remove markdown code blocks if present
        if result_text.startswith("```"):
            # Remove markdown code blocks
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        # Parse JSON response
        try:
            result_json = json.loads(result_text)
            
            # If it's wrapped in an object, try to find the array
            if isinstance(result_json, dict):
                # Look for common keys
                for key in ['classifications', 'results', 'papers', 'data', 'items']:
                    if key in result_json and isinstance(result_json[key], list):
                        return result_json[key]
                # If no key found, check if there's a single key with array value
                if len(result_json) == 1:
                    first_value = list(result_json.values())[0]
                    if isinstance(first_value, list):
                        return first_value
                print(f"Warning: Unexpected JSON structure in batch {batch_num}. Got dict: {list(result_json.keys())}")
                return []
            elif isinstance(result_json, list):
                return result_json
            else:
                print(f"Warning: Unexpected JSON type in batch {batch_num}: {type(result_json)}")
                return []
                
        except json.JSONDecodeError as e:
            # Try to extract JSON array from text
            import re
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            print(f"Warning: Could not parse JSON from batch {batch_num}: {e}")
            print(f"Response preview: {result_text[:200]}...")
            return []
        
    except Exception as e:
        print(f"Error classifying batch {batch_num}: {e}")
        return []


def classify_all_papers(results: Dict[str, Dict[str, Any]], top_org_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Classify papers in batches of 30.
    If top_org_ids is provided, only classify papers from those organizations.
    Returns dictionary mapping paper ID to classification result.
    Also adds classification to each paper object.
    """
    if not OPENAI_CLIENT:
        print("Skipping classification: OpenAI API key not configured.")
        return {}
    
    # Collect papers, filtering by top organizations if specified
    all_papers = []
    paper_to_journal = {}  # Map paper ID to journal code
    
    if top_org_ids:
        # Create a set for faster lookup
        top_org_set = set(top_org_ids)
        print(f"\nFiltering papers from top {len(top_org_ids)} organizations...")
    
    for journal_code, journal_data in results.items():
        papers = journal_data.get('papers', [])
        for paper in papers:
            paper_id = paper.get('id', '')
            if not paper_id:
                continue
            
            # If filtering by top organizations, check if paper has authors from top orgs
            if top_org_ids:
                authorships = paper.get('authorships', [])
                paper_has_top_org = False
                
                for authorship in authorships:
                    institutions = authorship.get('institutions', [])
                    for institution in institutions:
                        if institution and institution.get('id'):
                            inst_id = institution['id']
                            if inst_id in top_org_set:
                                paper_has_top_org = True
                                break
                    if paper_has_top_org:
                        break
                
                if not paper_has_top_org:
                    continue  # Skip papers not from top organizations
            
            all_papers.append(paper)
            paper_to_journal[paper_id] = journal_code
    
    total_papers = len(all_papers)
    if top_org_ids:
        print(f"Found {total_papers} papers from top {len(top_org_ids)} organizations")
    print(f"\nClassifying {total_papers} papers in batches of 30...")
    
    classifications = {}
    batch_size = 30
    
    for i in range(0, total_papers, batch_size):
        batch = all_papers[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_papers + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} papers)...")
        
        batch_results = classify_papers_batch(batch, batch_num)
        
        # Map results back to papers
        for j, paper in enumerate(batch):
            paper_id = paper.get('id', '')
            if j < len(batch_results):
                classification = batch_results[j]
                classifications[paper_id] = classification
                # Add classification to paper object
                paper['classification'] = classification
            else:
                # Default classification if API didn't return enough results
                default_class = {
                    "label": "Core AI & Data Science Methods",
                    "confidence": 0.5,
                    "why": "Classification unavailable"
                }
                classifications[paper_id] = default_class
                paper['classification'] = default_class
        
        # Rate limiting - wait between batches
        if i + batch_size < total_papers:
            time.sleep(1)  # 1 second delay between batches
    
    print(f"✓ Classified {len(classifications)} papers")
    return classifications


def calculate_category_stats(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics for each category.
    Returns dictionary with category counts and percentages.
    """
    category_counts = {category: 0 for category in PAPER_CATEGORIES}
    total = 0
    
    for journal_code, journal_data in results.items():
        papers = journal_data.get('papers', [])
        for paper in papers:
            classification = paper.get('classification')
            if classification:
                label = classification.get('label', '')
                if label in category_counts:
                    category_counts[label] += 1
                    total += 1
    
    # Calculate percentages
    category_stats = {}
    for category, count in category_counts.items():
        percentage = (count / total * 100) if total > 0 else 0
        category_stats[category] = {
            "count": count,
            "percentage": round(percentage, 1)
        }
    
    return {
        "categories": category_stats,
        "total": total
    }


def generate_journals_html(results: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate HTML page with journal results.
    """
    total_papers = sum(journal['paper_count'] for journal in results.values())
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAlex Paper Fetcher - Results</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .summary {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .nav-link {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }
        
        .nav-link:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .content {
            padding: 30px;
        }
        
        .journal-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .journal-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .journal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .journal-name {
            font-size: 1.4em;
            font-weight: 600;
            color: #333;
        }
        
        .journal-code {
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }
        
        .journal-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .info-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
        }
        
        .info-label {
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        
        .info-value {
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
        }
        
        .count-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 1.1em;
            font-weight: 600;
            display: inline-block;
        }
        
        .papers-list {
            margin-top: 15px;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 10px;
            background: white;
        }
        
        .paper-item {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.2s;
        }
        
        .paper-item:hover {
            background: #f8f9fa;
        }
        
        .paper-item:last-child {
            border-bottom: none;
        }
        
        .paper-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .paper-meta {
            font-size: 0.85em;
            color: #666;
        }
        
        .paper-link {
            color: #667eea;
            text-decoration: none;
            margin-left: 10px;
        }
        
        .paper-link:hover {
            text-decoration: underline;
        }
        
        .no-papers {
            text-align: center;
            padding: 20px;
            color: #999;
            font-style: italic;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }
        
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 OpenAlex Paper Fetcher</h1>
            <div class="summary">
                Total Papers Fetched: <span class="count-badge">""" + str(total_papers) + """</span>
            </div>
            <a href="organization_rankings.html" class="nav-link">View Organization Rankings →</a>
        </div>
        
        <div class="content">
"""
    
    for journal_code, journal_data in results.items():
        html += f"""
            <div class="journal-card">
                <div class="journal-header">
                    <div class="journal-name">{journal_data['name']}</div>
                    <div class="journal-code">{journal_code}</div>
                </div>
                
                <div class="journal-info">
                    <div class="info-item">
                        <div class="info-label">ISSN</div>
                        <div class="info-value">{journal_data['issn']}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Papers Count</div>
                        <div class="info-value">{journal_data['paper_count']}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Source ID</div>
                        <div class="info-value">{journal_data['source_id'] or 'N/A'}</div>
                    </div>
                </div>
"""
        
        if journal_data['paper_count'] > 0:
            html += """
                <div class="papers-list">
"""
            for paper in journal_data['papers'][:50]:  # Show first 50 papers
                title = paper.get('title', 'No title')
                doi = paper.get('doi', '')
                publication_date = paper.get('publication_date', 'N/A')
                openalex_url = paper.get('id', '')
                
                html += f"""
                    <div class="paper-item">
                        <div class="paper-title">{title}</div>
                        <div class="paper-meta">
                            Published: {publication_date}
                            {f'<a href="https://doi.org/{doi}" target="_blank" class="paper-link">DOI</a>' if doi else ''}
                            {f'<a href="{openalex_url}" target="_blank" class="paper-link">OpenAlex</a>' if openalex_url else ''}
                        </div>
                    </div>
"""
            
            if journal_data['paper_count'] > 50:
                html += f"""
                    <div class="paper-item" style="text-align: center; color: #666; font-style: italic;">
                        ... and {journal_data['paper_count'] - 50} more papers
                    </div>
"""
            
            html += """
                </div>
"""
        else:
            html += """
                <div class="no-papers">
                    No papers found for this journal
                </div>
"""
        
        html += """
            </div>
"""
    
    html += """
        </div>
"""
    
    html += """
        
        <div class="footer">
            Data fetched from <a href="https://openalex.org" target="_blank" style="color: #667eea;">OpenAlex</a> API
        </div>
    </div>
</body>
</html>
"""
    
    return html


def generate_rankings_html(org_rankings: List[Dict[str, Any]], total_papers: int, category_stats: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate HTML page with organization rankings and category statistics.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Organization Rankings - OpenAlex Paper Fetcher</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .summary {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .nav-link {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }
        
        .nav-link:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .content {
            padding: 30px;
        }
        
        .ranking-section {
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 2em;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        
        .ranking-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .ranking-table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .ranking-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .ranking-table td {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .ranking-table tbody tr {
            transition: background 0.2s;
        }
        
        .ranking-table tbody tr:hover {
            background: #f8f9fa;
        }
        
        .ranking-table tbody tr:last-child td {
            border-bottom: none;
        }
        
        .rank-number {
            font-weight: 700;
            font-size: 1.2em;
            color: #667eea;
            text-align: center;
            width: 60px;
        }
        
        .org-name {
            font-weight: 600;
            color: #333;
        }
        
        .org-country {
            font-size: 0.9em;
            color: #666;
            margin-top: 3px;
        }
        
        .org-count {
            font-weight: 600;
            color: #333;
            text-align: center;
        }
        
        .org-link {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }
        
        .org-link:hover {
            text-decoration: underline;
        }
        
        .count-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 1.1em;
            font-weight: 600;
            display: inline-block;
        }
        
        .category-stats {
            margin-bottom: 40px;
        }
        
        .category-stats-title {
            font-size: 1.8em;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        
        .category-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .category-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .category-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .category-name {
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        
        .category-count {
            font-size: 2em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .category-percentage {
            font-size: 0.9em;
            color: #666;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Organization Rankings</h1>
            <div class="summary">
                Total Papers Analyzed: <span class="count-badge">""" + str(total_papers) + """</span>
            </div>
            <a href="papers_results.html" class="nav-link">← Back to Journals</a>
        </div>
        
        <div class="content">
"""
    
    # Add category statistics section
    if category_stats and category_stats.get('categories'):
        html += """
            <div class="category-stats">
                <div class="category-stats-title">📊 Paper Categories</div>
                <div class="category-grid">
"""
        
        categories = category_stats['categories']
        total_classified = category_stats.get('total', 0)
        
        # Sort categories by count (descending)
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        for category_name, stats in sorted_categories:
            count = stats['count']
            percentage = stats['percentage']
            
            html += f"""
                    <div class="category-card">
                        <div class="category-name">{category_name}</div>
                        <div class="category-count">{count}</div>
                        <div class="category-percentage">{percentage}% of {total_classified} papers</div>
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="ranking-section">
                <div class="section-title">Top Organizations by Paper Count</div>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th style="width: 80px;">Rank</th>
                            <th>Organization</th>
                            <th style="width: 100px; text-align: center;">Total</th>
                            <th style="width: 120px; text-align: center;">Accounting & Financial AI</th>
                            <th style="width: 120px; text-align: center;">Business Intelligence</th>
                            <th style="width: 120px; text-align: center;">Information Systems</th>
                            <th style="width: 120px; text-align: center;">Engineering & Industrial</th>
                            <th style="width: 120px; text-align: center;">Core AI & Data Science</th>
                            <th style="width: 100px;">Link</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    else:
        html += """
            <div class="ranking-section">
                <div class="section-title">Top Organizations by Paper Count</div>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th style="width: 80px;">Rank</th>
                            <th>Organization</th>
                            <th style="width: 100px; text-align: center;">Total</th>
                            <th style="width: 120px; text-align: center;">Accounting & Financial AI</th>
                            <th style="width: 120px; text-align: center;">Business Intelligence</th>
                            <th style="width: 120px; text-align: center;">Information Systems</th>
                            <th style="width: 120px; text-align: center;">Engineering & Industrial</th>
                            <th style="width: 120px; text-align: center;">Core AI & Data Science</th>
                            <th style="width: 100px;">Link</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    if org_rankings and len(org_rankings) > 0:
        for rank, org in enumerate(org_rankings, 1):
            org_name = org.get('name', 'Unknown Institution')
            org_count = org.get('paper_count', 0)
            org_country = org.get('country', 'N/A')
            org_url = org.get('openalex_url', '')
            category_counts = org.get('category_counts', {})
            
            # Get counts for each category
            acc_fin_ai = category_counts.get('Accounting & Financial AI', 0)
            bus_intel = category_counts.get('Business Intelligence & Decision Support', 0)
            info_sys = category_counts.get('Information Systems & Applied Analytics', 0)
            eng_ind = category_counts.get('Engineering & Industrial AI', 0)
            core_ai = category_counts.get('Core AI & Data Science Methods', 0)
            
            html += f"""
                        <tr>
                            <td class="rank-number">{rank}</td>
                            <td>
                                <div class="org-name">{org_name}</div>
                                <div class="org-country">Country: {org_country}</div>
                            </td>
                            <td class="org-count" style="font-weight: 700; font-size: 1.1em;">{org_count}</td>
                            <td class="org-count">{acc_fin_ai}</td>
                            <td class="org-count">{bus_intel}</td>
                            <td class="org-count">{info_sys}</td>
                            <td class="org-count">{eng_ind}</td>
                            <td class="org-count">{core_ai}</td>
                            <td>
                                {f'<a href="{org_url}" target="_blank" class="org-link">OpenAlex</a>' if org_url else 'N/A'}
                            </td>
                        </tr>
"""
    else:
        html += """
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 40px; color: #999;">
                                No organization data available
                            </td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            Data fetched from <a href="https://openalex.org" target="_blank" style="color: #667eea;">OpenAlex</a> API
        </div>
    </div>
</body>
</html>
"""
    
    return html


def main():
    """
    Main function to fetch papers and generate HTML.
    """
    print("Starting OpenAlex paper fetcher...")
    print(f"Journals to process: {len(JOURNALS)}")
    
    # Fetch papers for all journals
    results = fetch_all_journal_papers()
    
    # Extract and rank organizations
    print("\n" + "="*60)
    print("Extracting organizations from papers...")
    print("="*60)
    organizations = extract_organizations_from_papers(results)
    print(f"Found {len(organizations)} unique organizations")
    
    # Rank organizations
    org_rankings = rank_organizations(organizations, top_n=50)
    print(f"Top 50 organizations identified")
    
    # Print top 10 for preview
    if org_rankings:
        print("\nTop 10 Organizations:")
        for i, org in enumerate(org_rankings[:10], 1):
            print(f"  {i}. {org['name']} ({org['country']}): {org['paper_count']} papers")
    
    # Get top 50 organization IDs for filtering
    top_50_org_ids = [org['openalex_url'] for org in org_rankings] if org_rankings else []
    
    # Classify papers from top 50 organizations only
    print("\n" + "="*60)
    print("Classifying papers from top 50 organizations...")
    print("="*60)
    classifications = classify_all_papers(results, top_org_ids=top_50_org_ids)
    
    # Calculate category statistics
    category_stats = calculate_category_stats(results)
    print(f"\nCategory Statistics:")
    for category, stats in category_stats['categories'].items():
        print(f"  {category}: {stats['count']} papers ({stats['percentage']}%)")
    
    # Save classifications to JSON
    classifications_data = {
        "total_papers": sum(journal['paper_count'] for journal in results.values()),
        "classified_papers": len(classifications),
        "category_statistics": category_stats,
        "classifications": []
    }
    
    # Add individual paper classifications
    for journal_code, journal_data in results.items():
        papers = journal_data.get('papers', [])
        for paper in papers:
            paper_id = paper.get('id', '')
            classification = paper.get('classification', {})
            if classification:
                classifications_data["classifications"].append({
                    "paper_id": paper_id,
                    "title": paper.get('title', 'No title'),
                    "journal": journal_code,
                    "category": classification.get('label', 'Unknown'),
                    "confidence": classification.get('confidence', 0),
                    "reasoning": classification.get('why', '')
                })
    
    classifications_file = "paper_classifications.json"
    with open(classifications_file, 'w', encoding='utf-8') as f:
        json.dump(classifications_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Classifications saved to {classifications_file}")
    
    # Generate HTML files
    total_papers = sum(journal['paper_count'] for journal in results.values())
    
    # Generate journals HTML
    journals_html = generate_journals_html(results)
    journals_file = "papers_results.html"
    with open(journals_file, 'w', encoding='utf-8') as f:
        f.write(journals_html)
    
    # Generate rankings HTML with category stats
    rankings_html = generate_rankings_html(org_rankings, total_papers, category_stats)
    rankings_file = "organization_rankings.html"
    with open(rankings_file, 'w', encoding='utf-8') as f:
        f.write(rankings_html)
    
    print(f"\n{'='*60}")
    print("✓ HTML files generated successfully!")
    print(f"✓ Journals page: {journals_file}")
    print(f"✓ Rankings page: {rankings_file}")
    print(f"{'='*60}")
    
    # Print summary
    print("\nSummary:")
    total = 0
    for journal_code, journal_data in results.items():
        count = journal_data['paper_count']
        total += count
        print(f"  {journal_code}: {count} papers")
    print(f"\n  Total: {total} papers")


if __name__ == "__main__":
    main()
