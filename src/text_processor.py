import os
import csv
import json
import re
from typing import List, Tuple, Union, Pattern, Dict, Callable
from utils import ConfigManager

class TextProcessor:
    # Define available transformation operations
    TRANSFORM_OPERATIONS = {
        'capitalize': str.capitalize,
        'upper': str.upper,
        'lower': str.lower,
        'strip': str.strip,
        'title': str.title
    }

    @staticmethod
    def load_find_replace_rules(file_path: str) -> List[Tuple[Union[str, Pattern], str]]:
        """
        Load find/replace rules from either a CSV file or JSON file.
        
        Args:
            file_path: Path to the rules file (.txt/.csv for simple rules, .json for advanced rules)
            
        Returns:
            List of (find, replace) tuples where find can be either a string or compiled regex
        """
        if not file_path or not os.path.exists(file_path):
            return []
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.json':
            return TextProcessor._load_json_rules(file_path)
        else:  # .txt, .csv, or any other extension
            return TextProcessor._load_simple_rules(file_path)

    @staticmethod
    def _load_simple_rules(file_path: str) -> List[Tuple[str, str]]:
        """Load simple text-based find/replace rules from a CSV file."""
        rules = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, skipinitialspace=True)
                for row in reader:
                    # Skip empty lines and comments
                    if not row or row[0].startswith('#'):
                        continue
                    if len(row) >= 2:
                        find_term = row[0].strip()
                        replace_term = row[1].strip()
                        if find_term and replace_term:
                            rules.append((find_term, replace_term))
        except Exception as e:
            ConfigManager.console_print(f"Error loading simple find/replace rules: {str(e)}")
            return []
        return rules

    @staticmethod
    def _load_json_rules(file_path: str) -> List[Tuple[Union[str, Pattern], str, List[Dict], Dict]]:
        """Load advanced find/replace rules from a JSON file."""
        rules = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for rule in data:
                    if not isinstance(rule, dict):
                        continue

                    if rule.get('enabled', True) is False:
                        continue  # Skip disabled rules

                    rule_type = rule.get('type', '').lower()
                    find_term = rule.get('find', '').strip()
                    replace_term = rule.get('replace', '').strip()
                    transforms = rule.get('transforms', [])
                    metadata = {
                        'id': rule.get('id', ''),
                        'comment': rule.get('comment', '')
                    }

                    if not find_term or not replace_term:
                        continue

                    if rule_type == 'regex':
                        try:
                            pattern = re.compile(find_term)
                            rules.append((pattern, replace_term, transforms, metadata))
                        except re.error as e:
                            ConfigManager.console_print(f"Invalid regex pattern '{find_term}': {str(e)}")
                    elif rule_type == 'simple':
                        rules.append((find_term, replace_term, transforms, metadata))

        except Exception as e:
            ConfigManager.console_print(f"Error loading JSON find/replace rules: {str(e)}")
            return []
        return rules

    @staticmethod
    def apply_find_replace_rules(text: str, rules: List[Tuple[Union[str, Pattern], str, List[Dict], Dict]]) -> str:
        """Apply find and replace rules to the text."""
        if not text or not rules:
            return text

        result = text
        for rule in rules:
            if len(rule) == 4:
                find_term, replace_term, transforms, metadata = rule
                rule_id = metadata.get('id', '')
                comment = metadata.get('comment', '')
            else:
                # Fallback if using legacy 3-item rules
                find_term, replace_term, transforms = rule
                metadata = {}
                rule_id = comment = ''

            if isinstance(find_term, Pattern):
                # Create a replacement function that applies transformations
                def replacement_func(match):
                    res = replace_term
                    # Replace $1, $2 etc. with actual group contents
                    for i in range(len(match.groups()) + 1):
                        group_content = match.group(i) if i > 0 else match.group()
                        if group_content is None:
                            continue
                        for transform in transforms:
                            if transform.get('group') == i:
                                for operation in transform.get('operations', []):
                                    if operation in TextProcessor.TRANSFORM_OPERATIONS:
                                        group_content = TextProcessor.TRANSFORM_OPERATIONS[operation](group_content)
                        res = res.replace(f'${i}', group_content)
                    return res

                before = result
                result = find_term.sub(replacement_func, result)
                if result != before and rule_id:
                    print(f"[Rule matched] ID: {rule_id} | {comment}")
            
            else:
                # Handle simple word replacements (preserve existing behavior)
                words = result.split()
                for i, word in enumerate(words):
                    stripped_word = word.strip('.,!?')
                    if stripped_word.lower() == find_term.lower():
                        punctuation = word[len(stripped_word):]
                        words[i] = replace_term + punctuation
                new_result = ' '.join(words)
                if new_result != result and rule_id:
                    print(f"[Rule matched] ID: {rule_id} | {comment}")
                result = new_result

        return result

