"""
AI Agent Safety & Compliance Engine
Acts as a guardian layer between AI and user
Ensures trustworthy, compliant, and accurate financial advice
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SafetyEngine:
    """
    Safety & Compliance Engine for AI financial responses
    Implements fiduciary duty safeguards
    """
    
    def __init__(self):
        self.rules = {
            'hallucination': self.check_hallucination,
            'calculation': self.validate_calculations,
            'compliance': self.check_compliance,
            'privacy': self.check_privacy,
            'disclaimer': self.check_disclaimer,
            'confidence': self.calculate_confidence
        }
        
        # SEBI/RBI prohibited terms
        self.prohibited_terms = [
            'guaranteed returns', 'risk-free', '100% safe',
            'assured profit', 'no loss', 'double your money',
            'secure profit', 'guaranteed income', 'no risk'
        ]
        
        # Required disclaimers
        self.required_disclaimers = [
            'consult a financial advisor',
            'professional advice',
            'not financial advice'
        ]
        
        self.violations = []
        self.warnings = []
    
    def process_response(self, response: str, context: Dict = None) -> Dict:
        """
        Main entry point: Process AI response through all safety checks
        
        Args:
            response: AI generated response
            context: User context (income, expenses, etc.)
        
        Returns:
            Dict with safety results
        """
        context = context or {}
        self.violations = []
        self.warnings = []
        
        results = {
            'original_response': response,
            'safe_response': response,
            'passed': True,
            'checks': {},
            'violations': [],
            'warnings': [],
            'confidence_score': 100,
            'confidence_level': 'high',
            'timestamp': datetime.now().isoformat()
        }
        
        # Run all checks
        for rule_name, check_func in self.rules.items():
            try:
                if rule_name == 'confidence':
                    result = check_func(response, context)
                    results['checks'][rule_name] = result
                    results['confidence_score'] = result.get('score', 100)
                    results['confidence_level'] = result.get('level', 'high')
                else:
                    passed, message = check_func(response, context)
                    results['checks'][rule_name] = {
                        'passed': passed,
                        'message': message
                    }
                    if not passed:
                        results['passed'] = False
                        results['violations'].append(message)
                        self.violations.append(message)
            except Exception as e:
                logger.error(f"Safety check '{rule_name}' failed: {e}")
                results['checks'][rule_name] = {
                    'passed': False,
                    'message': f"Check error: {str(e)}"
                }
                results['passed'] = False
        
        # Add warnings to results
        results['warnings'] = self.warnings
        
        # If violations, generate safe response
        if not results['passed']:
            results['safe_response'] = self.generate_safe_response(
                results['violations'],
                results['warnings']
            )
        
        return results
    
    def check_hallucination(self, response: str, context: Dict) -> Tuple[bool, str]:
        """Detect if AI invented numbers or facts not in context"""
        # Extract all numbers from response
        numbers = re.findall(r'₹?[\d,]+\.?\d*', response)
        
        if not numbers:
            return True, "No numbers found to verify"
        
        invented = []
        for num_str in numbers:
            clean_num = float(re.sub(r'[₹,]', '', num_str))
            # Check if number appears in context
            if not self._number_in_context(clean_num, context):
                invented.append(num_str)
        
        if invented:
            return False, f"⚠️ Hallucination detected: Invented numbers {invented}"
        
        return True, "✅ All numbers verified against context"
    
    def _number_in_context(self, number: float, context: Dict) -> bool:
        """Check if number exists in user context or is reasonable"""
        if not context:
            return False
        
        # Check against known user data
        known_fields = ['income', 'expenses', 'savings', 'investments', 'debt', 'emergency']
        
        for field in known_fields:
            if field in context and context[field]:
                # Check if number is within 10% of known value
                if abs(number - context[field]) / max(context[field], 1) < 0.1:
                    return True
        
        # Check if it's a percentage (0-100)
        if 0 <= number <= 100 and '%' in str(number):
            return True
        
        return False
    
    def validate_calculations(self, response: str, context: Dict) -> Tuple[bool, str]:
        """Validate mathematical calculations in response"""
        # Find simple arithmetic patterns: a + b = c, a * b = c, etc.
        calc_patterns = [
            (r'(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)', lambda a,b: a+b),
            (r'(\d+)\s*\*\s*(\d+)\s*=\s*(\d+)', lambda a,b: a*b),
            (r'(\d+)\s*-\s*(\d+)\s*=\s*(\d+)', lambda a,b: a-b),
            (r'(\d+)\s*/\s*(\d+)\s*=\s*(\d+)', lambda a,b: a/b if b != 0 else None)
        ]
        
        for pattern, operation in calc_patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                a, b, result = int(match[0]), int(match[1]), int(match[2])
                expected = operation(a, b)
                if expected is not None and abs(expected - result) > 0.01:
                    return False, f"❌ Invalid calculation: {match[0]} + {match[1]} != {result}"
        
        return True, "✅ All calculations are valid"
    
    def check_compliance(self, response: str, context: Dict) -> Tuple[bool, str]:
        """Check if advice complies with SEBI/RBI regulations"""
        response_lower = response.lower()
        
        violations = []
        for term in self.prohibited_terms:
            if term.lower() in response_lower:
                violations.append(term)
        
        if violations:
            return False, f"⚠️ Compliance violation: Prohibited terms: {violations}"
        
        return True, "✅ Complies with SEBI/RBI guidelines"
    
    def check_privacy(self, response: str, context: Dict) -> Tuple[bool, str]:
        """Check for PII/data privacy violations"""
        # Check for email exposure
        emails = re.findall(r'\S+@\S+\.\S+', response)
        if emails:
            return False, f"⚠️ Privacy violation: Email exposed: {emails[0]}"
        
        # Check for phone numbers (10 digits)
        phones = re.findall(r'\b\d{10}\b', response)
        if phones:
            return False, f"⚠️ Privacy violation: Phone number exposed"
        
        # Check for PAN (5 letters, 4 digits, 1 letter)
        pan = re.findall(r'[A-Z]{5}\d{4}[A-Z]', response)
        if pan:
            return False, f"⚠️ Privacy violation: PAN exposed"
        
        return True, "✅ No privacy violations detected"
    
    def check_disclaimer(self, response: str, context: Dict) -> Tuple[bool, str]:
        """Check if response includes required disclaimer"""
        response_lower = response.lower()
        
        has_disclaimer = any(
            term.lower() in response_lower 
            for term in self.required_disclaimers
        )
        
        if not has_disclaimer:
            self.warnings.append("Missing financial advisory disclaimer")
            return False, "⚠️ Missing required disclaimer"
        
        return True, "✅ Required disclaimer present"
    
    def calculate_confidence(self, response: str, context: Dict) -> Dict:
        """Calculate confidence score for response"""
        score = 100
        warnings = []
        
        # Check for missing user data
        if not context or not any(context.values()):
            score -= 25
            warnings.append("No user data available")
        
        # Check if response contains specific numbers
        if '₹' in response:
            score += 10  # More specific = more confident
        
        # Check if response contains percentages
        if '%' in response:
            score += 5
        
        # Check response length (too short = low confidence)
        words = len(response.split())
        if words < 10:
            score -= 15
            warnings.append("Response too brief")
        elif words < 20:
            score -= 10
        
        # Check for hedging language
        hedging = ['maybe', 'possibly', 'could', 'might', 'consider']
        for term in hedging:
            if term in response.lower():
                score -= 5
        
        # Check for disclaimer
        if any(term in response.lower() for term in self.required_disclaimers):
            score += 10
        
        # Apply final score bounds
        score = max(0, min(100, score))
        
        # Determine confidence level
        if score >= 80:
            level = 'high'
        elif score >= 50:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'score': score,
            'level': level,
            'warnings': warnings,
            'emoji': '🟢' if score >= 80 else '🟡' if score >= 50 else '🔴'
        }
    
    def generate_safe_response(self, violations: List[str], warnings: List[str]) -> str:
        """Generate a safe fallback response when violations are detected"""
        violation_text = '\n'.join([f"• {v}" for v in violations])
        warning_text = '\n'.join([f"• {w}" for w in warnings])
        warning_block = f"**Warnings:**\n{warning_text}" if warnings else ""
        
        return f"""
⚠️ **Safety Check: AI Response Modified**

The AI generated a response that didn't pass our safety checks.

**Issues detected:**
{violation_text}

{warning_block}

**Safe Response:**
I want to ensure I provide accurate financial guidance. 
Could you please share more details about your specific financial situation?

*Disclaimer: This is AI-generated financial guidance. Please consult a certified financial advisor before making important financial decisions.*
"""
    
    def get_safety_report(self, response: str, context: Dict = None) -> Dict:
        """Generate detailed safety report for logging/auditing"""
        results = self.process_response(response, context)
        
        return {
            'timestamp': results['timestamp'],
            'response_length': len(response),
            'passed': results['passed'],
            'violations': results['violations'],
            'warnings': results['warnings'],
            'confidence_score': results['confidence_score'],
            'confidence_level': results['confidence_level'],
            'checks': results['checks'],
            'summary': self._generate_summary(results)
        }
    
    def _generate_summary(self, results: Dict) -> str:
        """Generate human-readable summary"""
        if results['passed']:
            return "✅ All safety checks passed. Response is safe to display."
        else:
            return f"⚠️ {len(results['violations'])} safety violations detected. Response has been modified."