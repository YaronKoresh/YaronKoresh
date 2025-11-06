#!/usr/bin/env python3
"""
Test script to verify all external resources in the README are accessible.
This helps identify any broken images, badges, or stats APIs.
"""

import re
import requests
import time
from urllib.parse import urlparse
from collections import defaultdict

def extract_urls_from_readme(readme_file='README.md'):
    """Extract all URLs from the README file."""
    with open(readme_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all URLs in src, href attributes and markdown links
    url_pattern = r'(?:src|href)="([^"]+)"|!\[[^\]]*\]\(([^)]+)\)'
    urls = []
    
    for match in re.finditer(url_pattern, content):
        url = match.group(1) or match.group(2)
        if url and url.startswith('http'):
            urls.append(url)
    
    return urls


def test_url(url, timeout=10):
    """Test if a URL is accessible."""
    try:
        # Handle cache busting parameters
        test_url = re.sub(r'[?&]cache_bust=[^&]*', '', url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ProfileTester/1.0)'
        }
        
        response = requests.head(test_url, timeout=timeout, headers=headers, allow_redirects=True)
        
        # Try GET if HEAD fails
        if response.status_code >= 400:
            response = requests.get(test_url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
            response.close()
        
        return {
            'url': url,
            'status_code': response.status_code,
            'accessible': response.status_code < 400,
            'error': None
        }
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'status_code': None,
            'accessible': False,
            'error': 'Timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status_code': None,
            'accessible': False,
            'error': str(e)
        }


def categorize_url(url):
    """
    Categorize URL by its source domain for display purposes only.
    
    SECURITY NOTE: This function is used solely for categorizing URLs in test output.
    It is NOT used for URL sanitization or security validation. The test script only
    reads and displays URLs from the README - it does not process user input or make
    security decisions based on these categories.
    
    CodeQL Alert py/incomplete-url-substring-sanitization is a false positive here
    because this is not a sanitization function.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Note: This is for categorization/display only, not for security validation
    if domain.endswith('shields.io'):
        return 'Badge (shields.io)'
    elif domain.endswith('vercel.app') or domain.endswith('herokuapp.com'):
        return 'GitHub Stats API'
    elif domain.endswith('githubusercontent.com') or domain.endswith('github.com'):
        return 'GitHub Assets'
    else:
        return 'Other'


def main():
    print("🔍 Testing External Resources in README.md\n")
    print("=" * 80)
    
    # Extract URLs
    urls = extract_urls_from_readme()
    unique_urls = list(set(urls))
    
    print(f"\nFound {len(urls)} total URLs ({len(unique_urls)} unique)")
    
    # Categorize URLs
    by_category = defaultdict(list)
    for url in unique_urls:
        category = categorize_url(url)
        by_category[category].append(url)
    
    print("\nURL Categories:")
    for category, cat_urls in sorted(by_category.items()):
        print(f"  {category}: {len(cat_urls)} URLs")
    
    # Test each URL
    print("\n" + "=" * 80)
    print("Testing URLs...\n")
    
    results = {
        'passed': [],
        'failed': [],
        'timeout': []
    }
    
    for i, url in enumerate(unique_urls, 1):
        print(f"[{i}/{len(unique_urls)}] Testing: {url[:70]}...", end=' ', flush=True)
        
        result = test_url(url)
        
        if result['accessible']:
            print(f"✅ OK ({result['status_code']})")
            results['passed'].append(result)
        elif result['error'] == 'Timeout':
            print(f"⏱️  TIMEOUT")
            results['timeout'].append(result)
        else:
            print(f"❌ FAILED ({result['error']})")
            results['failed'].append(result)
        
        # Rate limiting
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total = len(unique_urls)
    passed = len(results['passed'])
    failed = len(results['failed'])
    timeout = len(results['timeout'])
    
    print(f"\n✅ Passed:  {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"❌ Failed:  {failed}/{total} ({failed/total*100:.1f}%)")
    print(f"⏱️  Timeout: {timeout}/{total} ({timeout/total*100:.1f}%)")
    
    if results['failed']:
        print("\n❌ Failed URLs:")
        for result in results['failed']:
            print(f"  - {result['url']}")
            print(f"    Error: {result['error']}")
    
    if results['timeout']:
        print("\n⏱️  Timed Out URLs:")
        for result in results['timeout']:
            print(f"  - {result['url']}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if failed > 0:
        print("\n⚠️  Some resources failed to load. Consider:")
        print("  1. Verify the URLs are correct")
        print("  2. Check if the services are temporarily down")
        print("  3. Ensure you have proper access to private resources")
        print("  4. Add more fallback mechanisms in the README")
    
    if timeout > 0:
        print("\n⚠️  Some resources timed out. This might indicate:")
        print("  1. Slow API responses (GitHub Stats APIs can be slow)")
        print("  2. Network connectivity issues")
        print("  3. Rate limiting by the service")
        print("  Note: The README includes onerror handlers for graceful degradation")
    
    if passed == total:
        print("\n✨ All resources are accessible! Great job!")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())
