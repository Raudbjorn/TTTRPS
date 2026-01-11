"""
html_parser.py - Parser for HTML documents

Dependencies:
    pip install beautifulsoup4 lxml html5lib
"""

import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from html.parser import HTMLParser as StdHTMLParser
import json

try:
    from bs4 import BeautifulSoup, Comment
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logging.info("BeautifulSoup4 not available - install with: pip install beautifulsoup4")

try:
    import lxml
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    logging.info("lxml not available - install with: pip install lxml")

try:
    import html5lib
    HTML5LIB_AVAILABLE = True
except ImportError:
    HTML5LIB_AVAILABLE = False
    logging.info("html5lib not available - install with: pip install html5lib")

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language


class HTMLStructureParser(StdHTMLParser):
    """Fallback HTML parser using standard library"""
    
    def __init__(self):
        super().__init__()
        self.elements = []
        self.current_tag = None
        self.current_attrs = {}
        self.text_content = []
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        self.elements.append({
            'type': 'start_tag',
            'tag': tag,
            'attrs': dict(attrs)
        })
    
    def handle_endtag(self, tag):
        self.elements.append({
            'type': 'end_tag',
            'tag': tag
        })
    
    def handle_data(self, data):
        if data.strip():
            self.text_content.append(data.strip())


class HTMLParser(BaseParser):
    """Parser for HTML documents with support for structure, scripts, and metadata"""
    
    def __init__(self):
        super().__init__()
        self.html_extensions = {'.html', '.htm', '.xhtml', '.xml', '.svg'}
        self.template_extensions = {'.ejs', '.erb', '.php', '.jsp', '.asp', '.aspx', '.hbs', '.njk', '.twig'}
        self.all_extensions = self.html_extensions | self.template_extensions
        
        self.html_indicators = [
            '<!DOCTYPE', '<html', '<head>', '<body>', '<div>', '<span>',
            '<script', '<style', '<meta', '<link', '<title>', '<p>',
            '<h1>', '<h2>', '<h3>', '<form>', '<input', '<button>'
        ]
        
        # Choose the best available parser
        if BS4_AVAILABLE and LXML_AVAILABLE:
            self.parser = 'lxml'
        elif BS4_AVAILABLE and HTML5LIB_AVAILABLE:
            self.parser = 'html5lib'
        elif BS4_AVAILABLE:
            self.parser = 'html.parser'
        else:
            self.parser = None
    
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() in self.all_extensions:
            return True
        
        # Check for HTML patterns
        content_lower = content.lower()[:1000]  # Check first 1KB
        
        # DOCTYPE declaration
        if '<!doctype html' in content_lower or '<!doctype html' in content_lower:
            return True
        
        # Count HTML indicators
        html_score = sum(1 for indicator in self.html_indicators if indicator.lower() in content_lower)
        
        # Check for XML declaration
        if content.strip().startswith('<?xml'):
            return True
        
        return html_score >= 3
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse HTML content"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        parsed_file = ParsedFile.empty(filepath, Language.UNKNOWN)
        
        try:
            if BS4_AVAILABLE:
                # Use BeautifulSoup for parsing
                soup = BeautifulSoup(content, self.parser if self.parser else 'html.parser')
                self._parse_with_beautifulsoup(soup, content, parsed_file)
            else:
                # Fallback to standard library parser
                self._parse_with_stdlib(content, parsed_file)
            
            # Detect template engine
            template_type = self._detect_template_engine(filepath, content)
            if template_type:
                parsed_file.metadata["template_engine"] = template_type
            
            # Detect framework
            framework = self._detect_framework(content, parsed_file)
            if framework:
                parsed_file.metadata["framework"] = framework
            
            # Add general metadata
            parsed_file.metadata.update({
                "lines": len(content.splitlines()),
                "is_html5": self._is_html5(content),
                "is_xhtml": self._is_xhtml(content),
                "is_xml": content.strip().startswith('<?xml'),
                "char_count": len(content),
                "has_forms": bool(parsed_file.metadata.get("forms", [])),
                "responsive": self._is_responsive(content, parsed_file)
            })
            
            return ParseResult(True, data=parsed_file)
            
        except Exception as e:
            error_msg = f"Error parsing HTML {filepath}: {str(e)}"
            self.logger.error(error_msg)
            parsed_file.parse_errors.append(error_msg)
            return ParseResult(True, data=parsed_file, warnings=[error_msg])
    
    def _parse_with_beautifulsoup(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse HTML using BeautifulSoup"""
        
        # Parse document metadata
        self._parse_metadata(soup, parsed_file)
        
        # Parse structure
        self._parse_structure(soup, content, parsed_file)
        
        # Parse scripts
        self._parse_scripts(soup, content, parsed_file)
        
        # Parse styles
        self._parse_styles(soup, content, parsed_file)
        
        # Parse forms
        self._parse_forms(soup, content, parsed_file)
        
        # Parse links and resources
        self._parse_links_and_resources(soup, parsed_file)
        
        # Parse semantic elements
        self._parse_semantic_elements(soup, content, parsed_file)
        
        # Parse data attributes
        self._parse_data_attributes(soup, parsed_file)
        
        # Parse comments
        self._parse_comments(soup, content, parsed_file)
        
        # Parse custom elements/web components
        self._parse_custom_elements(soup, parsed_file)
    
    def _parse_metadata(self, soup: 'BeautifulSoup', parsed_file: ParsedFile):
        """Parse HTML metadata from head section"""
        metadata = {}
        
        # Title
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)
            parsed_file.blocks.append(CodeBlock(
                type="metadata",
                name="title",
                content=str(title),
                signature="<title>",
                start_line=1,  # Would need proper line tracking
                end_line=1,
                language="html",
                metadata={"text": title.get_text(strip=True)}
            ))
        
        # Meta tags
        meta_tags = {}
        for meta in soup.find_all('meta'):
            if meta.get('name'):
                meta_tags[meta['name']] = meta.get('content', '')
            elif meta.get('property'):
                meta_tags[meta['property']] = meta.get('content', '')
            elif meta.get('charset'):
                meta_tags['charset'] = meta['charset']
            elif meta.get('http-equiv'):
                meta_tags[meta['http-equiv']] = meta.get('content', '')
        
        if meta_tags:
            metadata['meta_tags'] = meta_tags
            
            # Check for specific important meta tags
            if 'description' in meta_tags:
                metadata['description'] = meta_tags['description']
            if 'keywords' in meta_tags:
                metadata['keywords'] = meta_tags['keywords'].split(',')
            if 'viewport' in meta_tags:
                metadata['viewport'] = meta_tags['viewport']
            if 'author' in meta_tags:
                metadata['author'] = meta_tags['author']
        
        # Open Graph tags
        og_tags = {k: v for k, v in meta_tags.items() if k.startswith('og:')}
        if og_tags:
            metadata['open_graph'] = og_tags
        
        # Twitter Card tags
        twitter_tags = {k: v for k, v in meta_tags.items() if k.startswith('twitter:')}
        if twitter_tags:
            metadata['twitter_card'] = twitter_tags
        
        # Link tags
        link_tags = []
        for link in soup.find_all('link'):
            link_info = {
                'rel': link.get('rel', []),
                'href': link.get('href', ''),
                'type': link.get('type', '')
            }
            link_tags.append(link_info)
            
            # Track stylesheets
            if 'stylesheet' in link_info['rel']:
                parsed_file.imports.append(link_info['href'])
        
        if link_tags:
            metadata['link_tags'] = link_tags
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag['lang']
        
        parsed_file.metadata.update(metadata)
    
    def _parse_structure(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse HTML structure and create blocks for major sections"""
        
        # Parse major structural elements
        structural_tags = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        
        for tag_name in structural_tags:
            elements = soup.find_all(tag_name)
            for element in elements:
                # Get element position in content (approximate)
                element_str = str(element)[:100]  # First 100 chars for identification
                
                block = CodeBlock(
                    type="structure",
                    name=f"{tag_name}_{element.get('id', element.get('class', ['unnamed'])[0] if element.get('class') else 'unnamed')}",
                    content=str(element)[:500],  # Store first 500 chars
                    signature=f"<{tag_name}>",
                    start_line=1,  # Would need proper line tracking
                    end_line=1,
                    language="html",
                    metadata={
                        "tag": tag_name,
                        "id": element.get('id'),
                        "classes": element.get('class', []),
                        "attributes": element.attrs,
                        "text_length": len(element.get_text(strip=True))
                    }
                )
                parsed_file.blocks.append(block)
        
        # Count heading hierarchy
        headings = []
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            for h in h_tags:
                headings.append({
                    'level': i,
                    'text': h.get_text(strip=True),
                    'id': h.get('id'),
                    'classes': h.get('class', [])
                })
        
        if headings:
            parsed_file.metadata['headings'] = headings
            parsed_file.metadata['heading_count'] = len(headings)
    
    def _parse_scripts(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse JavaScript within HTML"""
        scripts = []
        
        for script in soup.find_all('script'):
            script_info = {
                'type': script.get('type', 'text/javascript'),
                'src': script.get('src'),
                'async': script.has_attr('async'),
                'defer': script.has_attr('defer'),
                'module': script.get('type') == 'module'
            }
            
            if script.string:  # Inline script
                script_content = script.string.strip()
                if script_content:
                    block = CodeBlock(
                        type="script",
                        name=f"inline_script_{len(scripts)}",
                        content=script_content,
                        signature="<script>",
                        start_line=1,  # Would need proper line tracking
                        end_line=1,
                        language="javascript",
                        metadata=script_info
                    )
                    parsed_file.blocks.append(block)
                    
                    # Try to detect what the script does
                    self._analyze_script_content(script_content, block)
            
            elif script_info['src']:  # External script
                parsed_file.imports.append(script_info['src'])
                scripts.append(script_info)
        
        if scripts:
            parsed_file.metadata['external_scripts'] = scripts
            parsed_file.metadata['script_count'] = len(scripts)
    
    def _parse_styles(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse CSS within HTML"""
        styles = []
        
        # Inline styles in <style> tags
        for style in soup.find_all('style'):
            style_content = style.string
            if style_content:
                block = CodeBlock(
                    type="style",
                    name=f"inline_style_{len(styles)}",
                    content=style_content.strip(),
                    signature="<style>",
                    start_line=1,  # Would need proper line tracking
                    end_line=1,
                    language="css",
                    metadata={
                        "type": style.get('type', 'text/css'),
                        "media": style.get('media'),
                        "scoped": style.has_attr('scoped')
                    }
                )
                parsed_file.blocks.append(block)
                
                # Analyze CSS content
                self._analyze_css_content(style_content, block)
                styles.append(block)
        
        # Elements with inline styles
        elements_with_styles = soup.find_all(style=True)
        if elements_with_styles:
            parsed_file.metadata['inline_styles_count'] = len(elements_with_styles)
            
            # Sample some inline styles
            inline_style_samples = []
            for element in elements_with_styles[:10]:  # First 10 samples
                inline_style_samples.append({
                    'tag': element.name,
                    'style': element['style'],
                    'id': element.get('id'),
                    'class': element.get('class')
                })
            parsed_file.metadata['inline_style_samples'] = inline_style_samples
    
    def _parse_forms(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse HTML forms"""
        forms = []
        
        for form in soup.find_all('form'):
            form_info = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'name': form.get('name'),
                'id': form.get('id'),
                'classes': form.get('class', []),
                'enctype': form.get('enctype'),
                'fields': []
            }
            
            # Parse form inputs
            for input_elem in form.find_all(['input', 'textarea', 'select', 'button']):
                field_info = {
                    'tag': input_elem.name,
                    'type': input_elem.get('type', 'text'),
                    'name': input_elem.get('name'),
                    'id': input_elem.get('id'),
                    'required': input_elem.has_attr('required'),
                    'placeholder': input_elem.get('placeholder')
                }
                
                # Special handling for select elements
                if input_elem.name == 'select':
                    options = [opt.get_text(strip=True) for opt in input_elem.find_all('option')]
                    field_info['options'] = options
                
                form_info['fields'].append(field_info)
            
            # Create a block for the form
            block = CodeBlock(
                type="form",
                name=form_info.get('id') or form_info.get('name') or f"form_{len(forms)}",
                content=str(form)[:500],  # First 500 chars
                signature=f"<form method='{form_info['method']}'>",
                start_line=1,  # Would need proper line tracking
                end_line=1,
                language="html",
                metadata=form_info
            )
            parsed_file.blocks.append(block)
            forms.append(form_info)
        
        if forms:
            parsed_file.metadata['forms'] = forms
            parsed_file.metadata['form_count'] = len(forms)
    
    def _parse_links_and_resources(self, soup: 'BeautifulSoup', parsed_file: ParsedFile):
        """Parse links and external resources"""
        
        # Anchors
        links = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href:
                link_info = {
                    'href': href,
                    'text': a.get_text(strip=True),
                    'target': a.get('target'),
                    'rel': a.get('rel'),
                    'type': self._classify_link(href)
                }
                links.append(link_info)
        
        if links:
            parsed_file.metadata['links'] = links
            parsed_file.metadata['link_count'] = len(links)
            
            # Classify links
            internal_links = [l for l in links if l['type'] == 'internal']
            external_links = [l for l in links if l['type'] == 'external']
            anchor_links = [l for l in links if l['type'] == 'anchor']
            
            parsed_file.metadata['internal_link_count'] = len(internal_links)
            parsed_file.metadata['external_link_count'] = len(external_links)
            parsed_file.metadata['anchor_link_count'] = len(anchor_links)
        
        # Images
        images = []
        for img in soup.find_all('img'):
            images.append({
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title'),
                'width': img.get('width'),
                'height': img.get('height'),
                'loading': img.get('loading'),  # lazy loading
                'srcset': img.get('srcset')  # responsive images
            })
        
        if images:
            parsed_file.metadata['images'] = images
            parsed_file.metadata['image_count'] = len(images)
            
            # Check for missing alt text (accessibility)
            missing_alt = sum(1 for img in images if not img['alt'])
            if missing_alt:
                parsed_file.metadata['images_missing_alt'] = missing_alt
        
        # Videos and Audio
        media = []
        for tag in soup.find_all(['video', 'audio']):
            media.append({
                'type': tag.name,
                'src': tag.get('src'),
                'controls': tag.has_attr('controls'),
                'autoplay': tag.has_attr('autoplay'),
                'muted': tag.has_attr('muted')
            })
        
        if media:
            parsed_file.metadata['media_elements'] = media
    
    def _parse_semantic_elements(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse HTML5 semantic elements"""
        semantic_tags = {
            'article': [],
            'section': [],
            'nav': [],
            'aside': [],
            'header': [],
            'footer': [],
            'main': [],
            'figure': [],
            'figcaption': [],
            'mark': [],
            'time': [],
            'details': [],
            'summary': []
        }
        
        for tag_name in semantic_tags:
            elements = soup.find_all(tag_name)
            for elem in elements:
                semantic_tags[tag_name].append({
                    'id': elem.get('id'),
                    'classes': elem.get('class', []),
                    'text_preview': elem.get_text(strip=True)[:100]
                })
        
        # Count semantic elements
        semantic_count = sum(len(v) for v in semantic_tags.values())
        if semantic_count > 0:
            parsed_file.metadata['semantic_elements'] = {k: v for k, v in semantic_tags.items() if v}
            parsed_file.metadata['semantic_element_count'] = semantic_count
            parsed_file.metadata['uses_semantic_html'] = True
    
    def _parse_data_attributes(self, soup: 'BeautifulSoup', parsed_file: ParsedFile):
        """Parse data-* attributes"""
        data_attributes = {}
        
        # Find all elements with data- attributes
        for element in soup.find_all(True):  # True finds all tags
            data_attrs = {k: v for k, v in element.attrs.items() if k.startswith('data-')}
            if data_attrs:
                for key, value in data_attrs.items():
                    if key not in data_attributes:
                        data_attributes[key] = []
                    data_attributes[key].append({
                        'tag': element.name,
                        'value': value,
                        'id': element.get('id'),
                        'class': element.get('class')
                    })
        
        if data_attributes:
            parsed_file.metadata['data_attributes'] = data_attributes
            parsed_file.metadata['unique_data_attributes'] = list(data_attributes.keys())
    
    def _parse_comments(self, soup: 'BeautifulSoup', content: str, parsed_file: ParsedFile):
        """Parse HTML comments"""
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        if comments:
            comment_blocks = []
            for i, comment in enumerate(comments):
                comment_text = comment.strip()
                if comment_text:
                    # Check for conditional comments (IE)
                    is_conditional = comment_text.startswith('[if') and comment_text.endswith('endif]')
                    
                    block = CodeBlock(
                        type="comment",
                        name=f"comment_{i}",
                        content=comment_text,
                        signature="<!-- -->",
                        start_line=1,  # Would need proper line tracking
                        end_line=1,
                        language="html",
                        metadata={
                            "is_conditional": is_conditional,
                            "length": len(comment_text)
                        }
                    )
                    parsed_file.blocks.append(block)
                    comment_blocks.append(comment_text[:100])  # Store preview
            
            parsed_file.metadata['comment_count'] = len(comments)
            parsed_file.metadata['comment_previews'] = comment_blocks[:10]  # First 10
    
    def _parse_custom_elements(self, soup: 'BeautifulSoup', parsed_file: ParsedFile):
        """Parse custom elements (Web Components)"""
        custom_elements = []
        
        # Find elements with hyphens in their names (custom element naming convention)
        for element in soup.find_all(True):
            if '-' in element.name:
                custom_elements.append({
                    'tag': element.name,
                    'id': element.get('id'),
                    'classes': element.get('class', []),
                    'attributes': list(element.attrs.keys())
                })
        
        if custom_elements:
            parsed_file.metadata['custom_elements'] = custom_elements
            parsed_file.metadata['custom_element_count'] = len(custom_elements)
            
            # Get unique custom element names
            unique_elements = list(set(elem['tag'] for elem in custom_elements))
            parsed_file.metadata['unique_custom_elements'] = unique_elements
    
    def _parse_with_stdlib(self, content: str, parsed_file: ParsedFile):
        """Fallback parser using standard library"""
        parser = HTMLStructureParser()
        parser.feed(content)
        
        # Basic structure detection
        tag_counts = {}
        for element in parser.elements:
            if element['type'] == 'start_tag':
                tag = element['tag']
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # Create blocks for important elements
                if tag in ['script', 'style', 'form', 'header', 'footer', 'nav', 'main']:
                    block = CodeBlock(
                        type=tag,
                        name=f"{tag}_{tag_counts[tag]}",
                        content=f"<{tag}>",  # Limited content in fallback mode
                        signature=f"<{tag}>",
                        start_line=1,
                        end_line=1,
                        language="html",
                        metadata={'attributes': element.get('attrs', {})}
                    )
                    parsed_file.blocks.append(block)
        
        parsed_file.metadata['tag_counts'] = tag_counts
        parsed_file.metadata['text_content'] = ' '.join(parser.text_content[:100])  # First 100 text nodes
    
    def _analyze_script_content(self, script: str, block: CodeBlock):
        """Analyze JavaScript content within script tags"""
        # Detect common libraries/frameworks
        if 'jQuery' in script or '$(' in script or '$.' in script:
            block.metadata['uses_jquery'] = True
        if 'React' in script or 'ReactDOM' in script:
            block.metadata['uses_react'] = True
        if 'Vue' in script or 'new Vue' in script:
            block.metadata['uses_vue'] = True
        if 'Angular' in script or 'ng-' in script:
            block.metadata['uses_angular'] = True
        
        # Detect common patterns
        if 'addEventListener' in script:
            block.metadata['has_event_listeners'] = True
        if 'fetch(' in script or 'XMLHttpRequest' in script:
            block.metadata['makes_api_calls'] = True
        if 'localStorage' in script or 'sessionStorage' in script:
            block.metadata['uses_storage'] = True
        if 'document.querySelector' in script or 'document.getElementById' in script:
            block.metadata['manipulates_dom'] = True
    
    def _analyze_css_content(self, css: str, block: CodeBlock):
        """Analyze CSS content within style tags"""
        # Detect CSS frameworks
        if 'bootstrap' in css.lower():
            block.metadata['uses_bootstrap'] = True
        if 'tailwind' in css.lower():
            block.metadata['uses_tailwind'] = True
        
        # Detect CSS features
        if '@media' in css:
            block.metadata['has_media_queries'] = True
        if '@keyframes' in css:
            block.metadata['has_animations'] = True
        if 'var(--' in css:
            block.metadata['uses_css_variables'] = True
        if 'grid' in css or 'flex' in css:
            block.metadata['uses_modern_layout'] = True
        
        # Count selectors (approximate)
        selector_count = len(re.findall(r'[^{]+{', css))
        block.metadata['selector_count'] = selector_count
    
    def _classify_link(self, href: str) -> str:
        """Classify a link as internal, external, anchor, etc."""
        if not href:
            return 'empty'
        elif href.startswith('#'):
            return 'anchor'
        elif href.startswith('mailto:'):
            return 'email'
        elif href.startswith('tel:'):
            return 'phone'
        elif href.startswith('javascript:'):
            return 'javascript'
        elif href.startswith(('http://', 'https://', '//')):
            return 'external'
        elif href.startswith('/'):
            return 'internal'
        else:
            return 'relative'
    
    def _is_html5(self, content: str) -> bool:
        """Check if document is HTML5"""
        return '<!DOCTYPE html>' in content or '<!doctype html>' in content.lower()
    
    def _is_xhtml(self, content: str) -> bool:
        """Check if document is XHTML"""
        return 'xmlns="http://www.w3.org/1999/xhtml"' in content
    
    def _is_responsive(self, content: str, parsed_file: ParsedFile) -> bool:
        """Check if HTML appears to be responsive"""
        indicators = []
        
        # Check for viewport meta tag
        if 'viewport' in parsed_file.metadata.get('meta_tags', {}):
            indicators.append('viewport')
        
        # Check for responsive CSS
        if '@media' in content:
            indicators.append('media_queries')
        
        # Check for responsive frameworks
        content_lower = content.lower()
        if 'bootstrap' in content_lower:
            indicators.append('bootstrap')
        if 'foundation' in content_lower:
            indicators.append('foundation')
        if 'tailwind' in content_lower:
            indicators.append('tailwind')
        
        # Check for responsive images
        if 'srcset' in content or 'picture' in content:
            indicators.append('responsive_images')
        
        return len(indicators) >= 2
    
    def _detect_template_engine(self, filepath: str, content: str) -> Optional[str]:
        """Detect template engine from file extension and content"""
        path = Path(filepath)
        ext = path.suffix.lower()
        
        # Extension-based detection
        template_map = {
            '.ejs': 'EJS',
            '.erb': 'ERB (Ruby)',
            '.php': 'PHP',
            '.jsp': 'JSP',
            '.asp': 'ASP',
            '.aspx': 'ASP.NET',
            '.hbs': 'Handlebars',
            '.njk': 'Nunjucks',
            '.twig': 'Twig',
            '.pug': 'Pug',
            '.jade': 'Jade'
        }
        
        if ext in template_map:
            return template_map[ext]
        
        # Content-based detection
        if '<%' in content and '%>' in content:
            if 'php' in content.lower():
                return 'PHP'
            return 'Server-side template'
        
        if '{{' in content and '}}' in content:
            if '{%' in content and '%}' in content:
                return 'Jinja2/Django/Twig'
            return 'Handlebars/Mustache'
        
        if '<?php' in content:
            return 'PHP'
        
        return None
    
    def _detect_framework(self, content: str, parsed_file: ParsedFile) -> Optional[str]:
        """Detect web framework or library"""
        frameworks = []
        content_lower = content.lower()
        
        # React
        if 'react' in content_lower or 'jsx' in content_lower:
            frameworks.append('React')
        
        # Vue
        if 'vue' in content_lower or 'v-model' in content or 'v-for' in content:
            frameworks.append('Vue.js')
        
        # Angular
        if 'angular' in content_lower or 'ng-' in content:
            frameworks.append('Angular')
        
        # jQuery
        if 'jquery' in content_lower or '$(document)' in content:
            frameworks.append('jQuery')
        
        # Bootstrap
        if 'bootstrap' in content_lower:
            frameworks.append('Bootstrap')
        
        # Tailwind
        if 'tailwind' in content_lower:
            frameworks.append('Tailwind CSS')
        
        return ', '.join(frameworks) if frameworks else None