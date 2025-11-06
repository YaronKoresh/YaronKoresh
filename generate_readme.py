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
                        'display_name': repo['name'].replace('-', ' ').title(),
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


def create_project_card(project):
    """Create an HTML/Markdown card for a single project."""
    name = project['display_name']
    desc = project['description']
    url = project['url']
    language = project.get('language')
    lang_badge = get_language_badge(language) if language else ''
    stars = project['stars']
    topics = project.get('topics', [])
    archived = project.get('archived', False)
    
    # Add archived badge if needed
    status = ""
    if archived:
        status = '<img src="https://img.shields.io/badge/Status-Archived-yellow?style=for-the-badge" alt="Archived"/><br/>'
    
    # Star badge
    star_badge = ""
    if stars > 0:
        star_badge = f'<img src="https://img.shields.io/badge/⭐_Stars-{stars}-yellow?style=for-the-badge" alt="{stars} stars"/><br/>'
    
    # Language badge
    lang_display = ""
    if lang_badge and language:
        lang_display = f'<img src="{lang_badge}" alt="{language}"/>'
    
    # Topic badges (limit to 3 for space)
    topic_badges = ""
    if topics:
        for topic in topics[:3]:
            topic_badges += f'<img src="https://img.shields.io/badge/-{topic.replace("-", "--")}-blue?style=flat-square" alt="{topic}"/> '
    
    card = f'''<div style="border: 1px solid #30363d; border-radius: 8px; padding: 20px; background: linear-gradient(145deg, rgba(36, 40, 59, 0.2), rgba(46, 51, 77, 0.2)); height: 100%; min-height: 200px;">
  <h3><a href="{url}" target="_blank">{name}</a></h3>
  {status}{star_badge}<p><em>{desc}</em></p>
  <div style="margin-top: 10px;">
    {lang_display}
  </div>
  {f'<div style="margin-top: 10px; font-size: 0.9em;">{topic_badges}</div>' if topic_badges else ''}
</div>'''
    return card


def generate_readme(repos):
    """Generate the complete README.md content from repository list."""
    
    # Header Section with error handling
    readme = f'''<div align="center">
  <img src="https://raw.githubusercontent.com/{PROFILE_REPO}/output/github-contribution-grid-snake-dark.svg?palette=github-dark" alt="GitHub Contribution Snake" onerror="this.style.display='none'"/>
</div>

<div align="center"><img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/section-header.svg" alt="" onerror="this.style.display='none'"/></div>

<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=30&pause=1000&color=58A6FF&center=true&vCenter=true&width=500&lines=Hi+there+%F0%9F%91%8B;I'm+{format_display_name(GITHUB_USERNAME).replace(' ', '+')};Developer+%26+Creator" alt="Typing SVG" onerror="this.style.display='none'"/>
</div>

<div align="center" style="background-color: #0D1117; border-radius: 8px; border: 1px solid #30363d; padding: 10px; margin: 40px auto 20px auto; max-width: 800px;">
  <p align="center">
    <a href="https://git.io/typing-svg">
      <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=15&pause=1000&color=A4D5FF&background=0D1117&center=true&vCenter=true&random=false&width=800&lines=I+believe+the+most+impactful+technology+arises+from+the+synthesis+of+disparate+fields.;My+work+is+a+continuous+exploration+of+this+principle;whether+applying+quantum+physics+to+secure+communications%2C;architecting+system-level+tools%2C+or+ensuring+digital+accessibility.;My+goal+is+not+just+to+write+code%2C+but+to+build+instruments;for+security%2C+for+efficiency%2C+and+for+creativity;that+empower+the+end-user+and+respect+their+autonomy." alt="Typing SVG" onerror="this.style.display='none'"/>
    </a>
  </p>
</div>

<div align="center">
  <a href="https://www.facebook.com/profile.php?id=100071801628056" target="_blank">
    <img src="https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white" alt="Facebook"/>
  </a>
  <a href="mailto:aharonkoresh1@gmail.com">
    <img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>
  </a>
</div>

<div align="center"><img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/section-header.svg" alt="" onerror="this.style.display='none'"/></div>

'''
    
    # Projects Section - no categories, just chronological order with featured first
    readme += f'''<h1 align='center'>🚀 My Projects <img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/blinking-cursor.svg" style="height: 24px; vertical-align: middle;" onerror="this.style.display='none'"/></h1>

<p align="center">Explore my diverse portfolio of {len(repos)} public projects, automatically updated from GitHub.</p>

'''
    
    if not repos:
        readme += '<p align="center"><em>No public repositories found.</em></p>\n\n'
    else:
        # Sort: featured first (by stars), then by last update
        featured = [r for r in repos if r.get('featured', False)]
        regular = [r for r in repos if not r.get('featured', False)]
        
        # Sort featured by stars (descending), regular by update time (descending)
        featured.sort(key=lambda x: x['stars'], reverse=True)
        regular.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        all_projects = featured + regular
        
        # Create table layout (4 columns)
        readme += '<table width="100%" border="0" cellspacing="0" cellpadding="0">\n'
        
        for i in range(0, len(all_projects), 4):
            readme += '<tr valign="top">\n'
            for j in range(4):
                if i + j < len(all_projects):
                    project = all_projects[i + j]
                    readme += f'<td width="25%" style="padding: 10px;">\n{create_project_card(project)}\n</td>\n'
                else:
                    readme += '<td width="25%" style="padding: 10px;"></td>\n'
            readme += '</tr>\n'
        
        readme += '</table>\n\n'
    
    # Stats Section with error handling
    # Calculate cache bust timestamp once for all stats images
    cache_bust_ts = datetime.now().timestamp()
    
    readme += f'''<div align="center"><img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/section-header.svg" alt="" onerror="this.style.display='none'"/></div>

<h1 align='center'>📚 My Skills <img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/blinking-cursor.svg" style="height: 24px; vertical-align: middle;" onerror="this.style.display='none'"/></h1>

<p align="center">
  <img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/skills.svg" alt="My Skills" onerror="this.style.display='none'"/>
</p>

<div align='center' style="margin-top: 30px;">
  <h1>🤝 Connect & Collaborate <img src="https://raw.githubusercontent.com/{PROFILE_REPO}/main/.github/assets/blinking-cursor.svg" style="height: 20px; vertical-align: middle;" onerror="this.style.display='none'"/></h1>
  <p>I'm always open to connecting with fellow developers, researchers, and creators.</p>
</div>

---

<div align="center">
  <sub>
    Last updated: {datetime.now().strftime('%B %d, %Y')}<br/>
    Generated automatically from GitHub API • <a href="https://github.com/{GITHUB_USERNAME}/{GITHUB_USERNAME}/actions">View Workflow</a>
  </sub>
</div>
'''
    
    return readme


def main():
    """Main function to generate README."""
    print("🚀 Generating Professional README with GitHub API...")
    print(f"📍 Target User: {GITHUB_USERNAME}")
    
    # Fetch repositories from GitHub API
    repos = fetch_github_repos()
    
    if not repos:
        print("⚠️  No repositories found. README will be generated with empty project list.")
    
    # Generate README
    readme_content = generate_readme(repos)
    
    # Write to file
    output_file = 'README.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✓ Generated {output_file}")
    print(f"  Total projects: {len(repos)}")
    if repos:
        featured_count = sum(1 for r in repos if r.get('featured', False))
        print(f"  Featured projects: {featured_count}")
        archived_count = sum(1 for r in repos if r.get('archived', False))
        if archived_count:
            print(f"  Archived projects: {archived_count}")
    
    print("\n✨ README.md has been generated successfully!")
    print("\n📝 The README is now automatically generated from GitHub API.")
    print("   It will update automatically via GitHub Actions workflow.")
    
    return 0  # Explicit return for success


if __name__ == '__main__':
    import sys
    sys.exit(main())
