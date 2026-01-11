"""
json_parser.py - Parser for JSON documents with semantic analysis

Why parse JSON when outputting JSON?
1. Extract semantic structure (schemas, patterns, relationships)
2. Generate meaningful descriptions for embeddings
3. Identify and document data types and constraints
4. Create hierarchical understanding of nested structures
5. Enable better RAG by adding context to raw data
"""

import json
import re
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language


@dataclass
class JSONSchema:
    """Inferred schema for JSON data"""
    type: str
    properties: Optional[Dict] = None
    items: Optional[Dict] = None
    examples: List[Any] = None
    nullable: bool = False
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class JSONParser(BaseParser):
    """Parser for JSON documents that extracts structure and meaning"""
    
    def __init__(self, enhance_for_embeddings: bool = True):
        super().__init__()
        self.json_extensions = {'.json', '.jsonl', '.ndjson', '.geojson', '.json5'}
        self.enhance_for_embeddings = enhance_for_embeddings
        
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() in self.json_extensions:
            return True
        
        # Try to parse as JSON
        try:
            json.loads(content.strip())
            return True
        except Exception:
            # Check for JSONL (newline-delimited JSON)
            try:
                lines = content.strip().split('\n')
                if lines and all(self._is_valid_json(line) for line in lines[:5] if line.strip()):
                    return True
            except Exception:
                pass
        
        return False
    
    def _is_valid_json(self, text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except Exception:
            return False
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse JSON content and extract structure"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        parsed_file = ParsedFile.empty(filepath, Language.UNKNOWN)
        
        try:
            # Detect JSON variant
            json_type = self._detect_json_type(content, filepath)
            
            if json_type == 'jsonl':
                self._parse_jsonl(content, parsed_file)
            else:
                # Parse regular JSON
                data = json.loads(content)
                self._parse_json_structure(data, parsed_file, content)
            
            # Add metadata
            parsed_file.metadata.update({
                "lines": len(content.splitlines()),
                "json_type": json_type,
                "size_bytes": len(content),
                "minified": not bool(re.search(r'\n\s+', content))
            })
            
            return ParseResult(True, data=parsed_file)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse error in {filepath}: Line {e.lineno}, Column {e.colno}: {e.msg}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
        except Exception as e:
            error_msg = f"Error parsing JSON {filepath}: {str(e)}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
    
    def _detect_json_type(self, content: str, filepath: str) -> str:
        """Detect the type of JSON file"""
        path = Path(filepath)
        
        if path.suffix in {'.jsonl', '.ndjson'}:
            return 'jsonl'
        elif path.suffix == '.geojson':
            return 'geojson'
        elif path.suffix == '.json5':
            return 'json5'
        
        # Check content
        lines = content.strip().split('\n')
        if len(lines) > 1:
            # Check if it's JSONL
            valid_json_lines = sum(1 for line in lines[:10] if line.strip() and self._is_valid_json(line.strip()))
            if valid_json_lines >= min(3, len(lines[:10])):
                return 'jsonl'
        
        # Check for GeoJSON
        try:
            data = json.loads(content)
            if isinstance(data, dict) and data.get('type') in ['Feature', 'FeatureCollection', 'Point', 'LineString', 'Polygon']:
                return 'geojson'
        except Exception:
            pass
        
        return 'json'
    
    def _parse_json_structure(self, data: Any, parsed_file: ParsedFile, raw_content: str):
        """Parse JSON structure and create semantic blocks"""
        
        # Infer schema
        schema = self._infer_schema(data)
        
        # Create main structure block
        main_block = CodeBlock(
            type="json_structure",
            name="root",
            content=json.dumps(data, indent=2)[:1000],  # First 1000 chars
            signature=f"JSON {schema.type}",
            start_line=1,
            end_line=len(raw_content.splitlines()),
            language="json",
            metadata={
                "schema_type": schema.type,
                "enhanced_description": self._generate_description(data, "root")
            }
        )
        parsed_file.blocks.append(main_block)
        
        # Parse based on structure type
        if isinstance(data, dict):
            self._parse_object(data, parsed_file, path="$")
        elif isinstance(data, list):
            self._parse_array(data, parsed_file, path="$")
        
        # Extract patterns and relationships
        patterns = self._extract_patterns(data)
        if patterns:
            parsed_file.metadata["patterns"] = patterns
        
        # Extract data statistics
        stats = self._calculate_statistics(data)
        parsed_file.metadata["statistics"] = stats
    
    def _parse_object(self, obj: Dict, parsed_file: ParsedFile, path: str = "$"):
        """Parse JSON object structure"""
        
        # Group related fields
        field_groups = self._group_fields(obj)
        
        for group_name, fields in field_groups.items():
            if len(fields) > 1:  # Only create blocks for actual groups
                group_data = {k: obj[k] for k in fields if k in obj}
                
                # Generate enhanced description for RAG
                description = self._generate_description(group_data, group_name)
                
                block = CodeBlock(
                    type="json_object_group",
                    name=group_name,
                    content=json.dumps(group_data, indent=2)[:500],
                    signature=f"Object Group: {group_name}",
                    start_line=0,
                    end_line=0,
                    language="json",
                    metadata={
                        "path": path,
                        "fields": fields,
                        "field_count": len(fields),
                        "enhanced_description": description,
                        "types": {k: type(v).__name__ for k, v in group_data.items()}
                    }
                )
                parsed_file.blocks.append(block)
        
        # Parse nested structures
        for key, value in obj.items():
            if isinstance(value, dict):
                self._parse_object(value, parsed_file, f"{path}.{key}")
            elif isinstance(value, list) and value:
                self._parse_array(value, parsed_file, f"{path}.{key}")
            
            # Create blocks for significant fields
            if self._is_significant_field(key, value):
                field_block = CodeBlock(
                    type="json_field",
                    name=key,
                    content=json.dumps({key: value}, indent=2)[:500],
                    signature=f"Field: {key}",
                    start_line=0,
                    end_line=0,
                    language="json",
                    metadata={
                        "path": f"{path}.{key}",
                        "type": type(value).__name__,
                        "enhanced_key": self._enhance_key_name(key),
                        "semantic_type": self._infer_semantic_type(key, value)
                    }
                )
                parsed_file.blocks.append(field_block)
    
    def _parse_array(self, arr: List, parsed_file: ParsedFile, path: str = "$"):
        """Parse JSON array structure"""
        if not arr:
            return
        
        # Analyze array patterns
        patterns = self._analyze_array_patterns(arr)
        
        # Sample items for schema inference
        sample_size = min(10, len(arr))
        sample = arr[:sample_size]
        
        # Infer item schema
        schemas = [self._infer_schema(item) for item in sample]
        
        # Check if homogeneous
        homogeneous = len(set(s.type for s in schemas)) == 1
        
        array_block = CodeBlock(
            type="json_array",
            name=f"array_at_{path}",
            content=json.dumps(sample, indent=2)[:500],
            signature=f"Array[{len(arr)}]",
            start_line=0,
            end_line=0,
            language="json",
            metadata={
                "path": path,
                "length": len(arr),
                "homogeneous": homogeneous,
                "item_type": schemas[0].type if homogeneous else "mixed",
                "patterns": patterns,
                "sample_description": self._generate_array_description(arr)
            }
        )
        parsed_file.blocks.append(array_block)
    
    def _parse_jsonl(self, content: str, parsed_file: ParsedFile):
        """Parse JSONL (newline-delimited JSON)"""
        lines = content.strip().split('\n')
        records = []
        errors = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                errors.append(f"Line {i+1}: {e.msg}")
        
        if records:
            # Analyze record structure
            schemas = [self._infer_schema(r) for r in records[:10]]
            homogeneous = len(set(str(s) for s in schemas)) == 1
            
            block = CodeBlock(
                type="jsonl_dataset",
                name="jsonl_records",
                content='\n'.join(json.dumps(r) for r in records[:3]),
                signature=f"JSONL Dataset [{len(records)} records]",
                start_line=1,
                end_line=len(lines),
                language="jsonl",
                metadata={
                    "record_count": len(records),
                    "homogeneous": homogeneous,
                    "errors": errors,
                    "schema": schemas[0].__dict__ if homogeneous else "mixed",
                    "enhanced_description": self._generate_dataset_description(records)
                }
            )
            parsed_file.blocks.append(block)
        
        parsed_file.metadata["jsonl_stats"] = {
            "total_lines": len(lines),
            "valid_records": len(records),
            "error_count": len(errors)
        }
    
    def _infer_schema(self, data: Any) -> JSONSchema:
        """Infer schema from JSON data"""
        if data is None:
            return JSONSchema(type="null", nullable=True)
        elif isinstance(data, bool):
            return JSONSchema(type="boolean", examples=[data])
        elif isinstance(data, int):
            return JSONSchema(type="integer", examples=[data])
        elif isinstance(data, float):
            return JSONSchema(type="number", examples=[data])
        elif isinstance(data, str):
            return JSONSchema(type="string", examples=[data[:100]])
        elif isinstance(data, list):
            if data:
                item_schemas = [self._infer_schema(item) for item in data[:5]]
                return JSONSchema(
                    type="array",
                    items=item_schemas[0].__dict__ if len(set(str(s) for s in item_schemas)) == 1 else {"type": "mixed"}
                )
            return JSONSchema(type="array", items={})
        elif isinstance(data, dict):
            properties = {}
            for key, value in list(data.items())[:20]:  # Limit to first 20 properties
                properties[key] = self._infer_schema(value).__dict__
            return JSONSchema(type="object", properties=properties)
        else:
            return JSONSchema(type="unknown")
    
    def _group_fields(self, obj: Dict) -> Dict[str, List[str]]:
        """Group related fields by common prefixes or patterns"""
        groups = defaultdict(list)
        
        # Group by common prefixes
        for key in obj.keys():
            # Check for underscore or camelCase prefixes
            if '_' in key:
                prefix = key.split('_')[0]
                if sum(1 for k in obj.keys() if k.startswith(prefix + '_')) >= 2:
                    groups[prefix].append(key)
                else:
                    groups['general'].append(key)
            elif re.match(r'^[a-z]+[A-Z]', key):  # camelCase
                prefix = re.match(r'^[a-z]+', key).group()
                if sum(1 for k in obj.keys() if k.startswith(prefix)) >= 2:
                    groups[prefix].append(key)
                else:
                    groups['general'].append(key)
            else:
                groups['general'].append(key)
        
        # Remove single-item groups
        return {k: v for k, v in groups.items() if len(v) > 1 or k == 'general'}
    
    def _is_significant_field(self, key: str, value: Any) -> bool:
        """Determine if a field is significant enough for its own block"""
        # Significant if:
        # - Contains nested structure
        # - Is a large array
        # - Has special semantic meaning
        # - Contains substantial text
        
        if isinstance(value, dict) and len(value) > 3:
            return True
        if isinstance(value, list) and len(value) > 5:
            return True
        if isinstance(value, str) and len(value) > 200:
            return True
        
        # Check for semantic significance
        significant_keys = ['id', 'name', 'type', 'description', 'url', 'path', 
                          'config', 'settings', 'data', 'results', 'error', 'message']
        if any(sig in key.lower() for sig in significant_keys):
            return True
        
        return False
    
    def _enhance_key_name(self, key: str) -> str:
        """Convert technical keys to human-readable descriptions"""
        # Handle snake_case
        if '_' in key:
            words = key.split('_')
        # Handle camelCase
        elif re.match(r'^[a-z]+[A-Z]', key):
            words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', key)
        else:
            words = [key]
        
        # Expand common abbreviations
        abbreviations = {
            'id': 'identifier',
            'msg': 'message',
            'config': 'configuration',
            'auth': 'authentication',
            'db': 'database',
            'api': 'API',
            'url': 'URL',
            'uri': 'URI',
            'json': 'JSON',
            'xml': 'XML',
            'html': 'HTML',
            'http': 'HTTP',
            'req': 'request',
            'res': 'response',
            'err': 'error',
            'val': 'value',
            'num': 'number',
            'str': 'string',
            'obj': 'object',
            'arr': 'array',
            'bool': 'boolean',
            'int': 'integer',
            'float': 'floating point',
            'desc': 'description',
            'addr': 'address',
            'tel': 'telephone',
            'img': 'image',
            'src': 'source',
            'dest': 'destination',
            'max': 'maximum',
            'min': 'minimum',
            'avg': 'average'
        }
        
        enhanced_words = []
        for word in words:
            lower_word = word.lower()
            if lower_word in abbreviations:
                enhanced_words.append(abbreviations[lower_word])
            else:
                enhanced_words.append(word.lower())
        
        return ' '.join(enhanced_words).capitalize()
    
    def _infer_semantic_type(self, key: str, value: Any) -> str:
        """Infer the semantic type of a field"""
        key_lower = key.lower()
        
        # Check key patterns
        if any(k in key_lower for k in ['email', 'mail']):
            return 'email'
        elif any(k in key_lower for k in ['phone', 'tel', 'mobile']):
            return 'phone'
        elif any(k in key_lower for k in ['url', 'link', 'href']):
            return 'url'
        elif any(k in key_lower for k in ['date', 'time', 'timestamp', 'created', 'updated', 'modified']):
            return 'datetime'
        elif any(k in key_lower for k in ['price', 'cost', 'amount', 'total', 'fee']):
            return 'currency'
        elif any(k in key_lower for k in ['lat', 'lon', 'latitude', 'longitude', 'coord']):
            return 'geographic'
        elif any(k in key_lower for k in ['id', 'identifier', 'uuid', 'guid']):
            return 'identifier'
        elif any(k in key_lower for k in ['name', 'title', 'label']):
            return 'name'
        elif any(k in key_lower for k in ['desc', 'description', 'summary', 'about']):
            return 'description'
        elif any(k in key_lower for k in ['pass', 'password', 'secret', 'token', 'key', 'credential']):
            return 'sensitive'
        
        # Check value patterns
        if isinstance(value, str):
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
                return 'email'
            elif re.match(r'^https?://', value):
                return 'url'
            elif re.match(r'^\d{4}-\d{2}-\d{2}', value):
                return 'date'
            elif re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value.lower()):
                return 'uuid'
        
        return 'general'
    
    def _generate_description(self, data: Any, context: str) -> str:
        """Generate a descriptive text for embeddings"""
        if not self.enhance_for_embeddings:
            return ""
        
        descriptions = []
        
        if isinstance(data, dict):
            descriptions.append(f"This {context} object contains {len(data)} fields")
            
            # Describe key fields
            for key, value in list(data.items())[:5]:
                enhanced_key = self._enhance_key_name(key)
                semantic_type = self._infer_semantic_type(key, value)
                
                if semantic_type != 'general':
                    descriptions.append(f"The {enhanced_key} field contains {semantic_type} data")
                elif isinstance(value, (list, dict)):
                    descriptions.append(f"The {enhanced_key} field contains structured {type(value).__name__} data")
                else:
                    descriptions.append(f"The {enhanced_key} field contains {type(value).__name__} data")
        
        elif isinstance(data, list):
            descriptions.append(f"This array contains {len(data)} items")
            if data:
                item_types = set(type(item).__name__ for item in data[:10])
                if len(item_types) == 1:
                    descriptions.append(f"All items are of type {item_types.pop()}")
                else:
                    descriptions.append(f"Items are of mixed types: {', '.join(item_types)}")
        
        return '. '.join(descriptions)
    
    def _generate_array_description(self, arr: List) -> str:
        """Generate description for array data"""
        if not arr:
            return "Empty array"
        
        descriptions = [f"Array with {len(arr)} items"]
        
        # Analyze first few items
        sample = arr[:5]
        if all(isinstance(item, dict) for item in sample):
            # Check for common keys
            all_keys = set()
            for item in sample:
                all_keys.update(item.keys())
            
            if all_keys:
                key_list = list(all_keys)[:5]
                enhanced_keys = [self._enhance_key_name(k) for k in key_list]
                descriptions.append(f"Each item contains fields like: {', '.join(enhanced_keys)}")
        
        return '. '.join(descriptions)
    
    def _generate_dataset_description(self, records: List[Dict]) -> str:
        """Generate description for JSONL dataset"""
        descriptions = [f"Dataset containing {len(records)} records"]
        
        if records:
            # Analyze schema consistency
            sample = records[:10]
            all_keys = set()
            for record in sample:
                if isinstance(record, dict):
                    all_keys.update(record.keys())
            
            if all_keys:
                descriptions.append(f"Records contain {len(all_keys)} different fields")
                key_sample = list(all_keys)[:5]
                enhanced_keys = [self._enhance_key_name(k) for k in key_sample]
                descriptions.append(f"Key fields include: {', '.join(enhanced_keys)}")
        
        return '. '.join(descriptions)
    
    def _analyze_array_patterns(self, arr: List) -> Dict[str, Any]:
        """Analyze patterns in array data"""
        patterns = {}
        
        if not arr:
            return patterns
        
        # Check if sorted
        if all(isinstance(item, (int, float, str)) for item in arr):
            patterns['sorted'] = arr == sorted(arr)
            patterns['reverse_sorted'] = arr == sorted(arr, reverse=True)
        
        # Check for unique values
        patterns['unique_values'] = len(arr) == len(set(str(item) for item in arr))
        
        # Check for time series pattern
        if all(isinstance(item, dict) for item in arr[:10]):
            # Look for timestamp fields
            for item in arr[:10]:
                for key in item.keys():
                    if any(t in key.lower() for t in ['time', 'date', 'timestamp']):
                        patterns['potential_time_series'] = True
                        break
        
        return patterns
    
    def _extract_patterns(self, data: Any) -> Dict[str, Any]:
        """Extract patterns and relationships from JSON data"""
        patterns = {}
        
        if isinstance(data, dict):
            # Check for common patterns
            keys = list(data.keys())
            
            # API response pattern
            if any(k in keys for k in ['status', 'data', 'message', 'error']):
                patterns['type'] = 'api_response'
            
            # Configuration pattern
            elif any(k in keys for k in ['config', 'settings', 'options', 'preferences']):
                patterns['type'] = 'configuration'
            
            # Database record pattern
            elif 'id' in keys and any(k in keys for k in ['created_at', 'updated_at', 'created', 'modified']):
                patterns['type'] = 'database_record'
            
            # GeoJSON pattern
            elif 'type' in data and 'coordinates' in data:
                patterns['type'] = 'geojson'
            
            # Check for hierarchical structure
            depth = self._calculate_depth(data)
            if depth > 3:
                patterns['structure'] = 'deeply_nested'
            elif depth > 1:
                patterns['structure'] = 'nested'
            else:
                patterns['structure'] = 'flat'
        
        return patterns
    
    def _calculate_depth(self, data: Any, current_depth: int = 0, max_depth: int = 10) -> int:
        """Calculate the maximum depth of nested structure"""
        if current_depth >= max_depth:
            return max_depth
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(self._calculate_depth(v, current_depth + 1, max_depth) for v in data.values())
        elif isinstance(data, list):
            if not data:
                return current_depth
            return max(self._calculate_depth(item, current_depth + 1, max_depth) for item in data[:10])
        else:
            return current_depth
    
    def _calculate_statistics(self, data: Any) -> Dict[str, Any]:
        """Calculate statistics about the JSON data"""
        stats = {
            'total_keys': 0,
            'total_values': 0,
            'max_depth': 0,
            'array_count': 0,
            'object_count': 0,
            'null_count': 0,
            'string_count': 0,
            'number_count': 0,
            'boolean_count': 0
        }
        
        def count_types(obj, depth=0):
            if isinstance(obj, dict):
                stats['object_count'] += 1
                stats['total_keys'] += len(obj)
                for value in obj.values():
                    count_types(value, depth + 1)
            elif isinstance(obj, list):
                stats['array_count'] += 1
                for item in obj:
                    count_types(item, depth + 1)
            else:
                stats['total_values'] += 1
                if obj is None:
                    stats['null_count'] += 1
                elif isinstance(obj, bool):
                    stats['boolean_count'] += 1
                elif isinstance(obj, str):
                    stats['string_count'] += 1
                elif isinstance(obj, (int, float)):
                    stats['number_count'] += 1
            
            stats['max_depth'] = max(stats['max_depth'], depth)
        
        count_types(data)
        return stats