"""
AI-Powered Financial Document Parser with OCR
Extracts financial data from images, PDFs, and documents
"""

import os
import re
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib

# OCR and Image Processing
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# NLP and ML
import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from langdetect import detect

import numpy as np


class DocumentParser:
    """
    Intelligent Financial Document Parser with OCR
    """
    
    def __init__(self):
        self.processor = None
        self.model = None
        self._initialize_models()
        
        # Category keywords
        self.category_keywords = {
            'Food': ['restaurant', 'cafe', 'meal', 'grocery', 'food', 'swiggy', 'zomato', 'dining'],
            'Transport': ['uber', 'ola', 'taxi', 'petrol', 'fuel', 'metro', 'bus', 'train', 'flight'],
            'Entertainment': ['netflix', 'amazon prime', 'movie', 'theatre', 'spotify', 'cinema'],
            'Shopping': ['amazon', 'flipkart', 'myntra', 'mall', 'shopping', 'retail'],
            'Utilities': ['electricity', 'water', 'gas', 'broadband', 'phone', 'internet', 'bill'],
            'Healthcare': ['hospital', 'doctor', 'medicine', 'clinic', 'medical', 'pharmacy'],
            'Rent': ['rent', 'lease', 'maintenance', 'society'],
            'Education': ['school', 'college', 'tuition', 'university', 'education'],
            'Insurance': ['insurance', 'premium', 'policy', 'life insurance', 'health insurance'],
            'Investment': ['sip', 'mutual fund', 'stock', 'investment', 'nps', 'ppf'],
            'Salary': ['salary', 'payroll', 'wages', 'income', 'earning'],
            'Other': []
        }
    
    def _initialize_models(self):
        """Initialize LayoutLMv3 models for document understanding"""
        try:
            self.processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
            self.model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")
            print("✅ LayoutLMv3 models loaded successfully")
        except Exception as e:
            print(f"⚠️ Could not load LayoutLMv3 models: {e}")
            self.processor = None
            self.model = None
    
    def extract_from_image(self, image_path: str) -> Dict:
        """
        Extract financial data from image
        
        Args:
            image_path: Path to image file
        
        Returns:
            Dict with extracted data
        """
        try:
            # Open image
            image = Image.open(image_path)
            
            # Preprocess image
            image = self._preprocess_image(image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            
            return self._parse_extracted_text(text, source='image')
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extract_from_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> Dict:
        """
        Extract financial data from PDF
        
        Args:
            pdf_path: Path to PDF file
            pages: Specific pages to extract (None = all pages)
        
        Returns:
            Dict with extracted data
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            if pages:
                images = [images[i] for i in pages if i < len(images)]
            
            all_text = ""
            for img in images:
                processed = self._preprocess_image(img)
                text = pytesseract.image_to_string(processed)
                all_text += text + "\n"
            
            return self._parse_extracted_text(all_text, source='pdf')
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extract_from_receipt(self, image_path: str) -> Dict:
        """
        Specialized extraction for receipts/invoices
        
        Args:
            image_path: Path to receipt image
        
        Returns:
            Dict with receipt data
        """
        try:
            # Extract text
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            
            # Parse receipt-specific data
            data = self._parse_receipt_text(text)
            data['source'] = 'receipt'
            
            return data
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _preprocess_image(self, image) -> Image:
        """Preprocess image for better OCR"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Resize if too large
        max_size = 2000
        if image.width > max_size or image.height > max_size:
            ratio = min(max_size / image.width, max_size / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def _parse_extracted_text(self, text: str, source: str = 'image') -> Dict:
        """
        Parse extracted text to extract financial entities
        
        Args:
            text: Extracted text
            source: Source type (image/pdf/receipt)
        
        Returns:
            Dict with structured data
        """
        # Clean text
        text = self._clean_text(text)
        
        # Extract entities
        transactions = self._extract_transactions(text)
        totals = self._extract_totals(text)
        dates = self._extract_dates(text)
        merchants = self._extract_merchants(text)
        
        # Categorize
        if transactions:
            for tx in transactions:
                tx['category'] = self._categorize_transaction(tx.get('description', ''))
        
        return {
            'success': True,
            'source': source,
            'raw_text': text,
            'extracted_data': {
                'transactions': transactions,
                'total_amount': totals,
                'dates': dates,
                'merchants': merchants,
                'document_type': self._detect_document_type(text),
                'confidence': 0.85
            },
            'text_preview': text[:500] + "..." if len(text) > 500 else text
        }
    
    def _parse_receipt_text(self, text: str) -> Dict:
        """
        Specialized parsing for receipts
        """
        text = self._clean_text(text)
        
        # Extract receipt-specific data
        data = {
            'success': True,
            'receipt_type': 'receipt',
            'total': self._extract_total_from_receipt(text),
            'items': self._extract_items_from_receipt(text),
            'date': self._extract_date_from_receipt(text),
            'merchant': self._extract_merchant_from_receipt(text),
            'tax': self._extract_tax_from_receipt(text)
        }
        
        return data
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters (keep numbers, letters, common symbols)
        text = re.sub(r'[^\w\s\.\,\-\₹\$\%\:\/]', '', text)
        
        return text
    
    def _extract_transactions(self, text: str) -> List[Dict]:
        """Extract transaction data from text"""
        transactions = []
        
        # Pattern: Amount with currency
        amount_pattern = r'(?:₹|\$)?\s*([\d,]+\.?\d*)\s*(?:₹|\$)?'
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Look for amount
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1).replace(',', ''))
                if amount > 0:
                    # Look for date
                    date_match = re.search(date_pattern, line)
                    date = date_match.group(1) if date_match else None
                    
                    # Get description (rest of the line without amount)
                    description = re.sub(amount_pattern, '', line).strip()
                    
                    # Look for merchant (usually before amount)
                    merchant = self._extract_merchant_from_line(line)
                    
                    transactions.append({
                        'amount': amount,
                        'date': date,
                        'description': description or 'Transaction',
                        'merchant': merchant,
                        'type': 'debit' if 'debit' in line.lower() or 'paid' in line.lower() else 'credit'
                    })
        
        return transactions
    
    def _extract_totals(self, text: str) -> Dict:
        """Extract total amounts"""
        totals = {}
        
        # Total amount
        total_patterns = [
            r'total\s*(?:amount)?\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'total\s*(?:amount)?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'amount\s*(?:due)?\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                totals['total'] = float(match.group(1).replace(',', ''))
                break
        
        return totals
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        dates = re.findall(date_pattern, text)
        
        # Also try to find dates in text format
        month_names = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        date_pattern_text = r'(\d{1,2}\s+' + month_names + r'\s+\d{2,4})'
        dates.extend(re.findall(date_pattern_text, text))
        
        return dates
    
    def _extract_merchants(self, text: str) -> List[str]:
        """Extract merchant names"""
        merchants = []
        
        # Common merchant indicators
        patterns = [
            r'(?:merchant|store|shop|company|from|at|to)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:paid\s+to|received\s+from)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            merchants.extend(matches)
        
        return merchants
    
    def _extract_merchant_from_line(self, line: str) -> Optional[str]:
        """Extract merchant from a single line"""
        # Look for merchant indicators
        patterns = [
            r'(?:at|from|to|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+.*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                merchant = match.group(1)
                # Clean up common false positives
                if merchant.lower() not in ['the', 'a', 'an', 'and', 'or', 'but']:
                    return merchant
        
        return None
    
    def _categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        description_lower = description.lower()
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category
        
        return 'Other'
    
    def _detect_document_type(self, text: str) -> str:
        """Detect document type"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['bank statement', 'account summary', 'transaction history']):
            return 'bank_statement'
        elif any(word in text_lower for word in ['invoice', 'bill', 'receipt', 'purchase']):
            return 'invoice'
        elif any(word in text_lower for word in ['salary', 'payroll', 'payslip']):
            return 'payslip'
        elif any(word in text_lower for word in ['investment', 'mutual fund', 'portfolio']):
            return 'investment'
        else:
            return 'general'
    
    def _extract_total_from_receipt(self, text: str) -> Optional[float]:
        """Extract total amount from receipt"""
        patterns = [
            r'total\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'amount\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'grand\s*total\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        
        return None
    
    def _extract_items_from_receipt(self, text: str) -> List[Dict]:
        """Extract line items from receipt"""
        items = []
        lines = text.split('\n')
        
        # Look for price patterns
        price_pattern = r'(?:₹|\$)?\s*([\d,]+\.?\d*)'
        
        for line in lines:
            match = re.search(price_pattern, line)
            if match and len(line) > 5:
                price = float(match.group(1).replace(',', ''))
                if price > 0:
                    item_name = re.sub(price_pattern, '', line).strip()
                    if item_name and len(item_name) > 2:
                        items.append({
                            'name': item_name,
                            'price': price
                        })
        
        return items
    
    def _extract_date_from_receipt(self, text: str) -> Optional[str]:
        """Extract date from receipt"""
        date_patterns = [
            r'date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_merchant_from_receipt(self, text: str) -> Optional[str]:
        """Extract merchant from receipt"""
        patterns = [
            r'(?:store|shop|merchant|company)\s*:?\s*([A-Za-z][A-Za-z\s]+)',
            r'^([A-Za-z][A-Za-z\s]+)$'
        ]
        
        lines = text.split('\n')
        if lines:
            # First few lines often contain merchant name
            for i in range(min(3, len(lines))):
                for pattern in patterns:
                    match = re.search(pattern, lines[i])
                    if match:
                        return match.group(1).strip()
        
        return None
    
    def _extract_tax_from_receipt(self, text: str) -> Optional[float]:
        """Extract tax amount from receipt"""
        patterns = [
            r'tax\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'gst\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)',
            r'vat\s*:?\s*(?:₹|\$)?\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        
        return None
    
    def export_to_expense(self, data: Dict) -> List[Dict]:
        """
        Export parsed data to expense format
        
        Args:
            data: Parsed document data
        
        Returns:
            List of expense dicts
        """
        expenses = []
        
        if not data.get('success'):
            return expenses
        
        extracted = data.get('extracted_data', {})
        transactions = extracted.get('transactions', [])
        
        for tx in transactions:
            expense = {
                'amount': tx.get('amount', 0),
                'category': tx.get('category', 'Other'),
                'merchant': tx.get('merchant', 'Unknown'),
                'date': tx.get('date', datetime.now().strftime('%Y-%m-%d')),
                'description': tx.get('description', 'Imported transaction'),
                'is_imported': True
            }
            expenses.append(expense)
        
        return expenses