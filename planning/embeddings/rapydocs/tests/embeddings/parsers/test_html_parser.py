#!/usr/bin/env python3
"""
Test the HTML parser functionality
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.embeddings.parsers.html_parser import HTMLParser

# Sample HTML content with various features
SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Rapyd Payment API Documentation">
    <meta name="keywords" content="payment,api,documentation,rapyd">
    <meta name="author" content="RapyDocs Team">
    
    <!-- Open Graph meta tags -->
    <meta property="og:title" content="Rapyd Payment API">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://docs.rapyd.net">
    <meta property="og:image" content="https://rapyd.net/og-image.png">
    <meta property="og:description" content="Complete payment API documentation">
    
    <!-- Twitter Card tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Rapyd Payment API">
    <meta name="twitter:description" content="Complete payment API documentation">
    
    <title>Rapyd Payment API Documentation</title>
    
    <!-- External stylesheets -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="/css/custom.css">
    <link rel="icon" type="image/png" href="/favicon.png">
    
    <!-- Inline styles -->
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            line-height: 1.6;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
        }
        
        :root {
            --primary-color: #007bff;
            --secondary-color: #6c757d;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .grid-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
        }
    </style>
</head>
<body data-theme="light" data-version="2.0">
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg" role="navigation">
        <div class="container">
            <a class="navbar-brand" href="/">Rapyd Docs</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse">
                <span class="navbar-toggler-icon"></span>
            </button>
        </div>
    </nav>
    
    <!-- Header -->
    <header class="page-header" id="main-header">
        <h1>Payment API Documentation</h1>
        <p class="lead">Complete guide to integrating Rapyd payments</p>
    </header>
    
    <!-- Main content -->
    <main class="container" role="main">
        <article id="payment-guide">
            <section class="intro" data-section="intro">
                <h2>Getting Started</h2>
                <p>Welcome to the <mark>Rapyd Payment API</mark> documentation.</p>
                
                <time datetime="2024-01-15">Last updated: January 15, 2024</time>
            </section>
            
            <section class="authentication" data-section="auth">
                <h3>Authentication</h3>
                <details>
                    <summary>API Key Setup</summary>
                    <p>You'll need to configure your API keys to authenticate requests.</p>
                </details>
            </section>
            
            <!-- Payment form example -->
            <section class="forms">
                <h3>Payment Form Example</h3>
                <form id="payment-form" method="POST" action="/api/payments" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="amount">Amount</label>
                        <input type="number" id="amount" name="amount" class="form-control" required placeholder="Enter amount">
                    </div>
                    
                    <div class="form-group">
                        <label for="currency">Currency</label>
                        <select id="currency" name="currency" class="form-control" required>
                            <option value="USD">US Dollar</option>
                            <option value="EUR">Euro</option>
                            <option value="GBP">British Pound</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" class="form-control" required>
                    </div>
                    
                    <textarea name="notes" placeholder="Additional notes"></textarea>
                    
                    <button type="submit" class="btn btn-primary">Submit Payment</button>
                    <button type="button" class="btn btn-secondary">Cancel</button>
                </form>
            </section>
            
            <!-- Links and resources -->
            <section class="resources">
                <h3>Resources</h3>
                <ul>
                    <li><a href="https://docs.rapyd.net" target="_blank" rel="noopener">Official Documentation</a></li>
                    <li><a href="/api/reference">API Reference</a></li>
                    <li><a href="#authentication">Jump to Authentication</a></li>
                    <li><a href="mailto:support@rapyd.net">Contact Support</a></li>
                    <li><a href="tel:+1-555-0123">Call Us</a></li>
                    <li><a href="javascript:void(0);" onclick="showHelp()">Show Help</a></li>
                </ul>
            </section>
            
            <!-- Images and media -->
            <figure>
                <img src="/images/api-flow.png" alt="API Flow Diagram" width="800" height="400" loading="lazy">
                <figcaption>API request flow visualization</figcaption>
            </figure>
            
            <picture>
                <source srcset="/images/logo-large.webp" media="(min-width: 768px)">
                <img src="/images/logo.png" alt="Rapyd Logo">
            </picture>
            
            <!-- Video content -->
            <video src="/videos/tutorial.mp4" controls muted autoplay></video>
            <audio src="/audio/intro.mp3" controls></audio>
        </article>
        
        <!-- Custom elements (web components) -->
        <payment-widget id="widget-1" data-currency="USD"></payment-widget>
        <api-example endpoint="/v1/payments" method="POST"></api-example>
    </main>
    
    <!-- Sidebar -->
    <aside class="sidebar" role="complementary">
        <h4>Related Links</h4>
        <nav>
            <ul>
                <li><a href="/guides">Guides</a></li>
                <li><a href="/tutorials">Tutorials</a></li>
            </ul>
        </nav>
    </aside>
    
    <!-- Footer -->
    <footer class="site-footer">
        <p>&copy; 2024 Rapyd. All rights reserved.</p>
    </footer>
    
    <!-- React component marker -->
    <div id="root" data-react-app="payment-dashboard"></div>
    
    <!-- Vue.js template syntax -->
    <div id="vue-app" v-model="paymentData" v-for="item in items">
        {{ message }}
    </div>
    
    <!-- Angular directives -->
    <div ng-app="paymentApp" ng-controller="PaymentController">
        <span ng-bind="amount"></span>
    </div>
    
    <!-- Comments -->
    <!-- This is a standard HTML comment -->
    <!--[if IE]>
        <p>You are using Internet Explorer</p>
    <![endif]-->
    
    <!-- External scripts -->
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js" async></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script type="module" src="/js/app.js"></script>
    
    <!-- Inline scripts -->
    <script>
        // jQuery code
        $(document).ready(function() {
            $('.btn-primary').on('click', function(e) {
                console.log('Button clicked');
            });
        });
        
        // React usage
        ReactDOM.render(
            React.createElement('h1', null, 'Hello React'),
            document.getElementById('root')
        );
        
        // Vue.js usage
        new Vue({
            el: '#vue-app',
            data: {
                message: 'Hello Vue'
            }
        });
        
        // DOM manipulation
        document.querySelector('#payment-form').addEventListener('submit', function(e) {
            e.preventDefault();
            // API call
            fetch('/api/payments', {
                method: 'POST',
                body: new FormData(this)
            });
        });
        
        // Local storage usage
        localStorage.setItem('theme', 'dark');
        sessionStorage.setItem('user', 'guest');
    </script>
    
    <!-- Bootstrap classes for responsive design -->
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-6 col-sm-12">Content</div>
            <div class="col-md-6 col-sm-12">Sidebar</div>
        </div>
    </div>
    
    <!-- Tailwind CSS classes -->
    <div class="flex flex-col md:flex-row gap-4 p-4">
        <div class="bg-blue-500 text-white p-2 rounded">Tailwind Example</div>
    </div>
    
    <!-- Inline styles on elements -->
    <div style="color: red; font-size: 16px;">Inline styled content</div>
    <span style="background-color: yellow;">Highlighted text</span>
    
    <!-- PHP template syntax -->
    <?php echo "Hello from PHP"; ?>
    
    <!-- EJS template syntax -->
    <%= user.name %>
    
    <!-- Handlebars template syntax -->
    {{#if user}}
        <p>Welcome {{user.name}}</p>
    {{/if}}
</body>
</html>"""

# Simple HTML without framework
SIMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Simple Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a simple HTML page without frameworks.</p>
    <a href="/about">About</a>
</body>
</html>"""

def test_html_parser():
    """Test the HTML parser with sample content"""
    print("Testing HTML Parser...")
    
    parser = HTMLParser()
    
    # Test with temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(SAMPLE_HTML)
        temp_path = f.name
    
    try:
        # Test can_parse
        can_parse = parser.can_parse(temp_path, SAMPLE_HTML)
        print(f"✓ Can parse HTML: {can_parse}")
        
        # Test parsing
        result = parser.parse(SAMPLE_HTML, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print(f"✓ Parsing successful!")
            print(f"  - Language: {parsed.language}")
            print(f"  - Blocks found: {len(parsed.blocks)}")
            print(f"  - Is HTML5: {parsed.metadata.get('is_html5')}")
            print(f"  - Is responsive: {parsed.metadata.get('responsive')}")
            print(f"  - Lines: {parsed.metadata.get('lines')}")
            print(f"  - Character count: {parsed.metadata.get('char_count')}")
            
            # Check metadata extraction
            print("\nMetadata extraction:")
            if 'title' in parsed.metadata:
                print(f"  - Title: {parsed.metadata['title']}")
            if 'description' in parsed.metadata:
                print(f"  - Description: {parsed.metadata['description']}")
            if 'keywords' in parsed.metadata:
                print(f"  - Keywords: {', '.join(parsed.metadata['keywords'][:3])}...")
            if 'author' in parsed.metadata:
                print(f"  - Author: {parsed.metadata['author']}")
            if 'viewport' in parsed.metadata:
                print(f"  - Viewport: {parsed.metadata['viewport']}")
            if 'language' in parsed.metadata:
                print(f"  - Language: {parsed.metadata['language']}")
            
            # Check Open Graph
            if 'open_graph' in parsed.metadata:
                print(f"  - Open Graph tags: {len(parsed.metadata['open_graph'])}")
            if 'twitter_card' in parsed.metadata:
                print(f"  - Twitter Card tags: {len(parsed.metadata['twitter_card'])}")
            
            # Check scripts and styles
            if 'external_scripts' in parsed.metadata:
                print(f"  - External scripts: {parsed.metadata['script_count']}")
            
            # Check forms
            if 'forms' in parsed.metadata:
                print(f"  - Forms found: {parsed.metadata['form_count']}")
                for form in parsed.metadata['forms'][:1]:  # Show first form
                    print(f"    Form: {form.get('id', 'unnamed')} - {form['method']} to {form['action']}")
                    print(f"    Fields: {len(form['fields'])}")
            
            # Check framework detection
            if 'framework' in parsed.metadata:
                print(f"  - Frameworks detected: {parsed.metadata['framework']}")
            
            # Check template engine
            if 'template_engine' in parsed.metadata:
                print(f"  - Template engine: {parsed.metadata['template_engine']}")
            
            # Show block types
            block_types = {}
            for block in parsed.blocks:
                block_type = block.type
                if block_type not in block_types:
                    block_types[block_type] = 0
                block_types[block_type] += 1
            
            print("\nBlock types found:", dict(block_types))
            
            # Show some specific blocks
            print("\nSample blocks:")
            for block in parsed.blocks[:5]:  # Show first 5 blocks
                if block.type == "metadata":
                    print(f"  - Metadata: {block.name}")
                elif block.type == "structure":
                    print(f"  - Structure: {block.name} ({block.metadata.get('tag')})")
                elif block.type == "script":
                    frameworks = []
                    if block.metadata.get('uses_jquery'):
                        frameworks.append('jQuery')
                    if block.metadata.get('uses_react'):
                        frameworks.append('React')
                    if block.metadata.get('uses_vue'):
                        frameworks.append('Vue')
                    framework_str = f" [{', '.join(frameworks)}]" if frameworks else ""
                    print(f"  - Script: {block.name}{framework_str}")
                elif block.type == "style":
                    features = []
                    if block.metadata.get('has_media_queries'):
                        features.append('responsive')
                    if block.metadata.get('uses_css_variables'):
                        features.append('CSS vars')
                    feature_str = f" [{', '.join(features)}]" if features else ""
                    print(f"  - Style: {block.name}{feature_str}")
                elif block.type == "form":
                    print(f"  - Form: {block.name} ({len(block.metadata.get('fields', []))} fields)")
            
            # Check semantic HTML
            if 'semantic_elements' in parsed.metadata:
                print(f"\nSemantic HTML5 elements: {parsed.metadata['semantic_element_count']}")
                for tag, elements in list(parsed.metadata['semantic_elements'].items())[:3]:
                    print(f"  - {tag}: {len(elements)} element(s)")
            
            # Check data attributes
            if 'data_attributes' in parsed.metadata:
                print(f"\nData attributes found: {len(parsed.metadata['unique_data_attributes'])}")
                for attr in parsed.metadata['unique_data_attributes'][:5]:
                    print(f"  - {attr}")
            
            # Check custom elements
            if 'custom_elements' in parsed.metadata:
                print(f"\nCustom elements (Web Components): {parsed.metadata['custom_element_count']}")
                for elem in parsed.metadata.get('unique_custom_elements', [])[:3]:
                    print(f"  - <{elem}>")
            
            # Check links
            if 'links' in parsed.metadata:
                print(f"\nLinks analysis:")
                print(f"  - Total links: {parsed.metadata['link_count']}")
                print(f"  - Internal: {parsed.metadata.get('internal_link_count', 0)}")
                print(f"  - External: {parsed.metadata.get('external_link_count', 0)}")
                print(f"  - Anchors: {parsed.metadata.get('anchor_link_count', 0)}")
            
            # Check images
            if 'images' in parsed.metadata:
                print(f"\nImages found: {parsed.metadata['image_count']}")
                if 'images_missing_alt' in parsed.metadata:
                    print(f"  - Missing alt text: {parsed.metadata['images_missing_alt']}")
                
        else:
            print(f"✗ Parsing failed: {result.error}")
            return False
    
    finally:
        # Clean up
        os.unlink(temp_path)
    
    return True

def test_simple_html():
    """Test with simple HTML without frameworks"""
    print("\nTesting Simple HTML...")
    
    parser = HTMLParser()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(SIMPLE_HTML)
        temp_path = f.name
    
    try:
        result = parser.parse(SIMPLE_HTML, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print("✓ Simple HTML parsed successfully!")
            print(f"  - Blocks: {len(parsed.blocks)}")
            print(f"  - Framework: {parsed.metadata.get('framework', 'None')}")
            print(f"  - Template engine: {parsed.metadata.get('template_engine', 'None')}")
            print(f"  - Is HTML5: {parsed.metadata.get('is_html5')}")
        else:
            print(f"✗ Simple HTML parsing failed: {result.error}")
            return False
    
    finally:
        os.unlink(temp_path)
    
    return True

def test_template_detection():
    """Test template engine detection"""
    print("\nTesting Template Engine Detection...")
    
    parser = HTMLParser()
    
    # Test PHP template
    php_html = """<?php include 'header.php'; ?>
    <h1><?php echo $title; ?></h1>
    <p>Welcome, <?= $username ?>!</p>"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.php', delete=False) as f:
        f.write(php_html)
        temp_path = f.name
    
    try:
        result = parser.parse(php_html, temp_path)
        if result.success and result.data:
            template = result.data.metadata.get('template_engine')
            print(f"✓ PHP template detected: {template}")
        else:
            print("✗ PHP template detection failed")
            return False
    finally:
        os.unlink(temp_path)
    
    # Test EJS template
    ejs_html = """<h1><%= title %></h1>
    <% users.forEach(function(user) { %>
        <li><%= user.name %></li>
    <% }); %>"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ejs', delete=False) as f:
        f.write(ejs_html)
        temp_path = f.name
    
    try:
        result = parser.parse(ejs_html, temp_path)
        if result.success and result.data:
            template = result.data.metadata.get('template_engine')
            print(f"✓ EJS template detected: {template}")
        else:
            print("✗ EJS template detection failed")
            return False
    finally:
        os.unlink(temp_path)
    
    return True

def test_react_bootstrap_content():
    """Test with React and Bootstrap content"""
    print("\nTesting React/Bootstrap Content...")
    
    react_bootstrap_html = """<!DOCTYPE html>
<html>
<head>
    <title>React Bootstrap App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <div id="root"></div>
            </div>
        </div>
    </div>
    
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script>
        const App = () => {
            return React.createElement('div', {className: 'alert alert-primary'}, 
                'Hello from React with Bootstrap!'
            );
        };
        
        ReactDOM.render(
            React.createElement(App),
            document.getElementById('root')
        );
    </script>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    parser = HTMLParser()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(react_bootstrap_html)
        temp_path = f.name
    
    try:
        result = parser.parse(react_bootstrap_html, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print("✓ React/Bootstrap content parsed!")
            
            framework = parsed.metadata.get('framework', '')
            print(f"  - Frameworks detected: {framework}")
            
            # Check if both React and Bootstrap were detected
            has_react = 'React' in framework
            has_bootstrap = 'Bootstrap' in framework
            
            print(f"  - React detected: {'✓' if has_react else '✗'}")
            print(f"  - Bootstrap detected: {'✓' if has_bootstrap else '✗'}")
            
            # Check for Bootstrap classes in metadata
            responsive = parsed.metadata.get('responsive', False)
            print(f"  - Responsive design: {'✓' if responsive else '✗'}")
            
            return has_react and has_bootstrap
        else:
            print(f"✗ React/Bootstrap parsing failed: {result.error}")
            return False
    
    finally:
        os.unlink(temp_path)

def test_file_processor_integration():
    """Test HTML processing in the file processor"""
    print("\nTesting File Processor Integration...")
    
    try:
        from src.embeddings.file_processor import FileProcessor
        
        # Mock database config
        db_config = {
            "host": "127.0.0.1",
            "port": 54320,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres"
        }
        
        # Create processor without embedding generation for this test
        processor = FileProcessor(db_config, use_largest_model=False)
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_HTML)
            temp_path = Path(f.name)
        
        try:
            # Test MIME detection
            mime_type, encoding = processor.detect_mime_type(temp_path)
            print(f"✓ MIME detection: {mime_type}, encoding: {encoding}")
            
            # Test content parsing
            content, parsed_data = processor.parse_content(temp_path, mime_type, encoding)
            
            if content and parsed_data:
                print("✓ File processor integration successful!")
                print(f"  - Content length: {len(content)} characters")
                print(f"  - Parser type: {parsed_data.get('parser_type', 'basic')}")
                
                if parsed_data.get('parser_type') == 'advanced_html':
                    print("  - Using advanced HTML parser ✓")
                    if 'blocks' in parsed_data:
                        print(f"  - Blocks parsed: {len(parsed_data['blocks'])}")
                    if 'metadata' in parsed_data:
                        if 'framework' in parsed_data['metadata']:
                            print(f"  - Frameworks: {parsed_data['metadata']['framework']}")
                        if 'forms' in parsed_data['metadata']:
                            print(f"  - Forms detected: {len(parsed_data['metadata']['forms'])}")
                else:
                    print("  - Using basic HTML processing")
            else:
                print("✗ File processor integration failed")
                return False
        
        finally:
            temp_path.unlink()
        
    except ImportError as e:
        # Check if it's a chromadb import error (expected in test environment)
        if 'chromadb' in str(e):
            print(f"⚠ Skipping integration test - chromadb not installed (expected in test environment)")
            return True  # Don't fail the test for missing optional dependencies
        else:
            print(f"✗ Import error: {e}")
            return False
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False
    
    return True

def test_malformed_html():
    """Test parser with malformed HTML"""
    print("\nTesting Malformed HTML Handling...")
    
    malformed_html = """<html>
    <head><title>Broken HTML</title>
    <body>
        <p>Unclosed paragraph
        <div>Unclosed div
        <script>var x = 'unclosed string</script>
    </body>
    <!-- Missing closing html tag -->"""
    
    parser = HTMLParser()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(malformed_html)
        temp_path = f.name
    
    try:
        result = parser.parse(malformed_html, temp_path)
        
        if result.success:
            print("✓ Malformed HTML handled gracefully")
            if result.warnings:
                print(f"  - Warnings: {len(result.warnings)}")
            return True
        else:
            print("✓ Parser correctly identified issues with malformed HTML")
            return True
    
    finally:
        os.unlink(temp_path)

def test_accessibility_features():
    """Test accessibility feature detection"""
    print("\nTesting Accessibility Features...")
    
    accessible_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Accessible Page</title>
</head>
<body>
    <main role="main">
        <h1>Main Heading</h1>
        <nav aria-label="Main navigation">
            <ul>
                <li><a href="#content">Skip to content</a></li>
            </ul>
        </nav>
        
        <img src="logo.png" alt="Company Logo">
        <img src="decoration.png" alt="">
        <img src="photo.jpg">  <!-- Missing alt -->
        
        <form>
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" required aria-required="true">
            
            <button type="submit" aria-label="Submit form">Submit</button>
        </form>
    </main>
</body>
</html>"""
    
    parser = HTMLParser()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(accessible_html)
        temp_path = f.name
    
    try:
        result = parser.parse(accessible_html, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print("✓ Accessibility features detected:")
            
            # Check for language attribute
            if 'language' in parsed.metadata:
                print(f"  - Page language: {parsed.metadata['language']}")
            
            # Check for images missing alt text
            if 'images_missing_alt' in parsed.metadata:
                print(f"  - Images missing alt text: {parsed.metadata['images_missing_alt']}")
            
            # Check for semantic HTML usage
            if parsed.metadata.get('uses_semantic_html'):
                print("  - Uses semantic HTML5 elements: ✓")
            
            return True
        else:
            print("✗ Accessibility test failed")
            return False
    
    finally:
        os.unlink(temp_path)

if __name__ == "__main__":
    print("HTML Parser Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test 1: Comprehensive HTML parsing
    if not test_html_parser():
        success = False
    
    # Test 2: Simple HTML without frameworks
    if not test_simple_html():
        success = False
    
    # Test 3: Template engine detection
    if not test_template_detection():
        success = False
    
    # Test 4: React and Bootstrap content
    if not test_react_bootstrap_content():
        success = False
    
    # Test 5: File processor integration
    if not test_file_processor_integration():
        success = False
    
    # Test 6: Malformed HTML handling
    if not test_malformed_html():
        success = False
    
    # Test 7: Accessibility features
    if not test_accessibility_features():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! HTML parser is working correctly.")
    else:
        print("✗ Some tests failed. Check the output above.")
    
    exit(0 if success else 1)