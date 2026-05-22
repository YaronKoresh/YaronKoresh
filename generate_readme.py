#!/usr/bin/env python3
"""
README Generator for GitHub Profile
This script automatically generates a professional README.md with all public projects
fetched from the GitHub API, with error handling for external resources.

This script is designed to be portable and can be easily transferred to any GitHub profile
by setting the GITHUB_USERNAME environment variable or by detecting it from git context.
"""

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def format_display_name(username):
    """
    Format username for display in the typing animation.
    Preserves camelCase names (e.g., 'YaronKoresh' -> 'Yaron Koresh'),
    converts hyphens/underscores to spaces for others (e.g., 'john-doe' -> 'John Doe').
    """
    # If username has no separators and contains uppercase letters (camelCase),
    # insert spaces before uppercase letters
    if '-' not in username and '_' not in username:
        # Check if it's camelCase (has both upper and lower case)
        if username != username.lower() and username != username.upper():
            # Insert space before each uppercase letter (except the first)
            formatted = re.sub(r'(?<!^)(?=[A-Z])', ' ', username)
            return formatted
    
    # Otherwise, replace separators with spaces and apply title case
    return username.replace('-', ' ').replace('_', ' ').title()


def get_github_username():
    """
    Automatically detect GitHub username from environment or git repository context.
    This makes the script portable across different repositories and users.
    """
    # First, try environment variable (set by GitHub Actions)
    username = os.environ.get('GITHUB_REPOSITORY_OWNER')
    if username:
        return username
    
    # Try GITHUB_REPOSITORY format: owner/repo
    repo = os.environ.get('GITHUB_REPOSITORY')
    if repo and '/' in repo:
        return repo.split('/')[0]
    
    # Try to get from git remote
    try:
        remote_url = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Parse different URL formats (HTTPS and SSH) to extract username
        # 
        # CodeQL Note: This is NOT URL sanitization for security purposes.
        # We are extracting the username component from a trusted git remote URL
        # to determine which GitHub user's repositories to fetch. The username is
        # only used in API calls to GitHub's public API (github.com/users/{username}/repos).
        # There is no security risk here as:
        # 1. Source is trusted (git config, not user input)
        # 2. No authentication/authorization decisions made
        # 3. No shell command injection (used only in API URL construction)
        # 4. API calls are made via urllib with proper encoding
        #
        # HTTPS format: https://github.com/username/repo.git
        # SSH format: git@github.com:username/repo.git
        
        username = None
        
        # Try HTTPS format - split at the exact protocol+domain
        if 'https://github.com/' in remote_url:
            parts = remote_url.split('https://github.com/', 1)
            if len(parts) == 2:
                username = parts[1].split('/')[0]
        
        # Try SSH format - split at the exact user@domain:
        elif 'git@github.com:' in remote_url:
            parts = remote_url.split('git@github.com:', 1)
            if len(parts) == 2:
                username = parts[1].split('/')[0]
        
        # Clean up username
        if username:
            username = username.rstrip('.git')
            if username:
                return username
                
    except (subprocess.CalledProcessError, FileNotFoundError):
        # It's expected that git config may not be available (e.g., outside a git repo).
        # In such cases, we fall back to a default username below.
        pass
    
    # Default fallback - fail gracefully with informative error
    print("⚠️  Warning: Could not detect GitHub username from environment or git config.")
    print("   Set GITHUB_REPOSITORY_OWNER environment variable or run in a GitHub repository.")
    print("   Using 'YaronKoresh' as fallback for compatibility.")
    return 'YaronKoresh'


# Configuration constants - now dynamic and portable
GITHUB_USERNAME = get_github_username()
PROFILE_REPO = f'{GITHUB_USERNAME}/{GITHUB_USERNAME}'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')  # Optional, for higher rate limits


def fetch_github_repos():
    """
    Fetch all public repositories for the user from GitHub API.
    Returns a list of repository dictionaries with relevant information.
    """
    repos = []
    page = 1
    per_page = 100
    
    print(f"📡 Fetching repositories for user: {GITHUB_USERNAME}")
    
    while True:
        url = f'https://api.github.com/users/{GITHUB_USERNAME}/repos?page={page}&per_page={per_page}&sort=updated'
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'GitHub-Profile-Generator/{GITHUB_USERNAME}'
        }
        
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if not data:
                    break
                
                # Filter and process repositories
                for repo in data:
                    # Skip private and forked repositories
                    if repo.get('private') or repo.get('fork'):
                        continue
                    
                    repos.append({
                        'name': repo['name'],
                        'display_name': format_display_name(repo['name']),
                        'description': repo.get('description') or 'No description available',
                        'url': repo['html_url'],
                        'language': repo.get('language'),
                        'stars': repo.get('stargazers_count', 0),
                        'topics': repo.get('topics', []),
                        'archived': repo.get('archived', False),
                        'featured': repo.get('stargazers_count', 0) >= 2,
                        'created_at': repo.get('created_at'),
                        'updated_at': repo.get('updated_at'),
                    })
                
                page += 1
                
        except HTTPError as e:
            if e.code == 404:
                print(f"❌ User '{GITHUB_USERNAME}' not found")
            else:
                print(f"❌ HTTP Error {e.code}: {e.reason}")
            break
        except URLError as e:
            print(f"❌ URL Error: {e.reason}")
            break
        except Exception as e:
            print(f"❌ Error fetching repositories: {e}")
            break
    
    print(f"✓ Found {len(repos)} public repositories")
    return repos


def fetch_github_profile():
    """Fetch GitHub user profile data (followers, account age, etc.)."""
    url = f'https://api.github.com/users/{GITHUB_USERNAME}'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': f'GitHub-Profile-Generator/{GITHUB_USERNAME}'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f'Warning: Could not fetch profile data: {e}')
        return {}


def get_language_badge(language):
    """Generate a badge URL for a programming language."""
    badges = {
        'Python': 'https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white',
        'JavaScript': 'https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black',
        'TypeScript': 'https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white',
        'Java': 'https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=java&logoColor=white',
        'C': 'https://img.shields.io/badge/C-00599C?style=for-the-badge&logo=c&logoColor=white',
        'C++': 'https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=cplusplus&logoColor=white',
        'C#': 'https://img.shields.io/badge/C%23-239120?style=for-the-badge&logo=csharp&logoColor=white',
        'Go': 'https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white',
        'Rust': 'https://img.shields.io/badge/Rust-000000?style=for-the-badge&logo=rust&logoColor=white',
        'Ruby': 'https://img.shields.io/badge/Ruby-CC342D?style=for-the-badge&logo=ruby&logoColor=white',
        'PHP': 'https://img.shields.io/badge/PHP-777BB4?style=for-the-badge&logo=php&logoColor=white',
        'Swift': 'https://img.shields.io/badge/Swift-FA7343?style=for-the-badge&logo=swift&logoColor=white',
        'Kotlin': 'https://img.shields.io/badge/Kotlin-0095D5?style=for-the-badge&logo=kotlin&logoColor=white',
        'Shell': 'https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnu-bash&logoColor=white',
        'HTML': 'https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white',
        'CSS': 'https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white',
        'Common Lisp': 'https://img.shields.io/badge/Lisp-3C5280?style=for-the-badge&logo=lisp&logoColor=white',
        'QML': 'https://img.shields.io/badge/QML-41CD52?style=for-the-badge&logo=qt&logoColor=white',
    }
    
    return badges.get(language, '')


LANGUAGE_META = {
    'Python':      ('3776AB', 'python',      'white'),
    'JavaScript':  ('F7DF1E', 'javascript',  'black'),
    'TypeScript':  ('3178C6', 'typescript',  'white'),
    'Java':        ('ED8B00', 'openjdk',     'white'),
    'C':           ('00599C', 'c',           'white'),
    'C++':         ('00599C', 'cplusplus',   'white'),
    'C#':          ('239120', 'csharp',      'white'),
    'Go':          ('00ADD8', 'go',          'white'),
    'Rust':        ('000000', 'rust',        'white'),
    'Ruby':        ('CC342D', 'ruby',        'white'),
    'PHP':         ('777BB4', 'php',         'white'),
    'Swift':       ('FA7343', 'swift',       'white'),
    'Kotlin':      ('0095D5', 'kotlin',      'white'),
    'Shell':       ('4EAA25', 'gnubash',     'white'),
    'HTML':        ('E34F26', 'html5',       'white'),
    'CSS':         ('1572B6', 'css3',        'white'),
    'Common Lisp': ('3C5280', None,          'white'),
    'QML':         ('41CD52', 'qt',          'white'),
}


# Ordered list of (category_label, topic_keywords). First match wins.
CATEGORY_KEYWORDS = [
    ('Security & Cryptography', {
        'cryptography', 'encryption', 'reverse-engineering', 'ghidra',
        'security', 'hash', 'encryption-decryption', 'cryptography-tools',
        'cipher', 'malware', 'forensics', 'pentest',
    }),
    ('Audio & Voice', {
        'audio', 'voice', 'music', 'acapella', 'rvc', 'audacity',
        'audio-processing', 'audio-analysis', 'acapella-extractor',
        'speech', 'tts', 'midi',
    }),
    ('AI & Data Science', {
        'artificial-intelligence', 'machine-learning', 'data-science',
        'deep-learning', 'cuda', 'ai-chatbot', 'llm', 'neural-network',
        'nlp', 'computer-vision',
    }),
    ('Developer Tools', {
        'cli', 'toolkit', 'tools', 'automation', 'packaging', 'codebase',
        'code-analysis', 'context-window', 'template-project', 'utility',
        'utilities', 'devtools', 'plugin', 'plugins',
    }),
    ('Web & Accessibility', {
        'web', 'browser', 'accessibility', 'frontend',
        'html', 'css', 'dom',
    }),
]


def language_stat_badge(lang, count):
    """Build a static shields.io badge for a language with repo count."""
    color, logo_name, logo_color = LANGUAGE_META.get(lang, ('555555', None, 'white'))
    # shields.io path encoding: '-' -> '--', '_' -> '__', ' ' -> '_'
    label = (
        lang.replace('-', '--').replace('_', '__')
            .replace(' ', '_').replace('+', '%2B').replace('#', '%23')
    )
    url = f'https://img.shields.io/badge/{label}-{count}-{color}?style=flat-square'
    if logo_name:
        url += f'&logo={logo_name}&logoColor={logo_color}'
    return f'<img src="{url}" alt="{lang}: {count} repos"/>'


def create_project_card(project):
    """Create an HTML/Markdown card for a single project."""
    name = project['display_name']
    desc = project['description']
    url = project['url']
    language = project.get('language')
    stars = project['stars']
    archived = project.get('archived', False)

    # Truncate long descriptions at a word boundary
    if len(desc) > 133:
        desc = desc[:130].rsplit(' ', 1)[0] + '...'

    # Language badge — flat-square to match stars badge
    lang_badge_html = ''
    if language and language in LANGUAGE_META:
        color, logo_name, logo_color = LANGUAGE_META[language]
        label = language.replace('-', '--').replace('_', '__').replace(' ', '_').replace('+', '%2B').replace('#', '%23')
        badge_url = f'https://img.shields.io/badge/{label}-{color}?style=flat-square'
        if logo_name:
            badge_url += f'&logo={logo_name}&logoColor={logo_color}'
        lang_badge_html = f'<img src="{badge_url}" alt="{language}"/>'

    # Badge row: stars, archived status, language — all flat-square
    badge_parts = []
    if stars > 0:
        badge_parts.append(f'<img src="https://img.shields.io/badge/Stars-{stars}-yellow?style=flat-square" alt="{stars} stars"/>')
    if archived:
        badge_parts.append('<img src="https://img.shields.io/badge/archived-lightgrey?style=flat-square" alt="Archived"/>')
    if lang_badge_html:
        badge_parts.append(lang_badge_html)

    # All content on one line — blank lines inside a GitHub HTML table break the parser
    parts = [f'<h3><a href="{url}" target="_blank">{name}</a></h3>']
    if badge_parts:
        parts.append('<p>' + ' &nbsp; '.join(badge_parts) + '</p>')
    if desc and desc != 'No description available':
        parts.append(f'<p><em>{desc}</em></p>')

    return '<div align="center">' + ''.join(parts) + '</div>'


def generate_readme(repos, profile=None):
    """Generate the complete README.md content from repository list."""
    
    # Compute all stats from locally fetched API data — no third-party services
    total_stars = sum(r.get('stars', 0) for r in repos)
    followers = profile.get('followers', 0) if profile else 0
    member_since = profile.get('created_at', '')[:4] if profile and profile.get('created_at') else ''
    lang_counts = Counter(r['language'] for r in repos if r.get('language'))
    top_langs = lang_counts.most_common(8)
    lang_badges_html = ' '.join(language_stat_badge(lang, count) for lang, count in top_langs)

    stats_cells = [
        f'<td align="center"><strong>{len(repos)}</strong><br/><sub>repositories</sub></td>',
        f'<td align="center"><strong>{total_stars}</strong><br/><sub>stars</sub></td>',
    ]
    if followers:
        stats_cells.append(f'<td align="center"><strong>{followers}</strong><br/><sub>followers</sub></td>')
    if member_since:
        stats_cells.append(f'<td align="center"><strong>{member_since}</strong><br/><sub>member since</sub></td>')
    stats_row = ''.join(stats_cells)

    # Header Section
    display_name = format_display_name(GITHUB_USERNAME)
    readme = f'''<h1 align="center">{display_name}</h1>
<h1 align="center">Software Developer &nbsp;&middot;&nbsp; Security &nbsp;&middot;&nbsp; Performance &nbsp;&middot;&nbsp; Accessibility</h1>

<p align="center">
I build tools at the intersection of security, performance, and digital accessibility.<br/>
From reverse-engineering and cryptography to system-level utilities and AI tooling,<br/>
my goal is to write software that is efficient, secure, and respects user autonomy.
</p>

<p align="center">
  <a href="mailto:aharonkoresh1@gmail.com">
    <img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>
  </a>
</p>

---

<h1 align="center">Overview</h1>

<table align="center"><tr>{stats_row}</tr></table>

<p align="center">{lang_badges_html}</p>

---

'''
    
    # Projects Section — grouped by category, profile meta-repo excluded
    project_repos = [r for r in repos if r['name'].lower() != GITHUB_USERNAME.lower()]

    readme += '<h1 align="center">Projects</h1>\n\n'

    if not project_repos:
        readme += '<p align="center"><em>No public repositories found.</em></p>\n\n'
    else:
        # Assign each repo to the first matching category
        categorized = {cat: [] for cat, _ in CATEGORY_KEYWORDS}
        categorized['Other'] = []
        for repo in project_repos:
            topics = set(repo.get('topics', []))
            matched = False
            for cat, keywords in CATEGORY_KEYWORDS:
                if topics & keywords:
                    categorized[cat].append(repo)
                    matched = True
                    break
            if not matched:
                categorized['Other'].append(repo)

        first_category = True
        for cat, cat_repos in categorized.items():
            if not cat_repos:
                continue
            # Sort by stars desc, then update time desc
            cat_repos.sort(key=lambda x: (x['stars'], x.get('updated_at', '')), reverse=True)
            cat_display = cat.replace('&', '&amp;')
            if first_category:
                first_category = False
            else:
                readme += '<hr/>\n\n'
            readme += f'<h2 align="center">{cat_display}</h2>\n\n'
            readme += '<table width="100%" border="0" cellspacing="0" cellpadding="12">\n'
            for i in range(0, len(cat_repos), 2):
                readme += '<tr valign="top">\n'
                for j in range(2):
                    if i + j < len(cat_repos):
                        project = cat_repos[i + j]
                        readme += f'<td width="50%" valign="top">{create_project_card(project)}</td>\n'
                    else:
                        readme += '<td width="50%"></td>\n'
                readme += '</tr>\n'
            readme += '</table>\n\n'
    
    skills_badges = ' '.join(
        f'<img src="{get_language_badge(lang)}" alt="{lang}"/>'
        for lang, _ in top_langs
        if get_language_badge(lang)
    )

    readme += f'''---

<h1 align="center">Technical Stack</h1>

<p align="center">{skills_badges}</p>

---

<h1 align="center">Connect</h1>

<p align="center">
Open to connecting with fellow developers and researchers.<br/>
Reach out via <a href="mailto:aharonkoresh1@gmail.com">email</a>.
</p>

---

<p align="center">
  <sub>Last updated: {datetime.now().strftime('%B %d, %Y')} &nbsp;&middot;&nbsp; Generated automatically from GitHub API &nbsp;&middot;&nbsp; <a href="https://github.com/{GITHUB_USERNAME}/{GITHUB_USERNAME}/actions">View Workflow</a></sub>
</p>
'''
    
    return readme


def main():
    """Main function to generate README."""
    print(f"Generating README for: {GITHUB_USERNAME}")

    # Fetch profile and repositories from GitHub API
    profile = fetch_github_profile()
    repos = fetch_github_repos()

    if not repos:
        print("Warning: No repositories found. README will be generated with empty project list.")

    # Generate README
    readme_content = generate_readme(repos, profile)

    # Write to file
    output_file = 'README.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"Generated {output_file} with {len(repos)} projects")
    return 0
if __name__ == '__main__':
    import sys
    sys.exit(main())
