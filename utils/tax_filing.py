"""
Automated Tax Filing Integration with ITR Generation
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import pdfplumber
import os


class TaxFilingSystem:
    """
    Complete Tax Filing System with ITR Generation
    """
    
    def __init__(self, user_data: Dict):
        """
        Initialize tax filing system with user data
        
        Args:
            user_data: Dict with user financial data
        """
        self.user = user_data
        self.income = self.calculate_income()
        self.deductions = self.calculate_deductions()
        self.tax_regime = user_data.get('tax_regime', 'new')
    
    def calculate_income(self) -> Dict:
        """Calculate all income sources"""
        return {
            'salary': self.user.get('salary', 0),
            'business': self.user.get('business_income', 0),
            'capital_gains': self.user.get('capital_gains', 0),
            'house_property': self.user.get('rental_income', 0),
            'other': self.user.get('other_income', 0),
            'total': sum([
                self.user.get('salary', 0),
                self.user.get('business_income', 0),
                self.user.get('capital_gains', 0),
                self.user.get('rental_income', 0),
                self.user.get('other_income', 0)
            ])
        }
    
    def calculate_deductions(self) -> Dict:
        """Calculate all deductions"""
        return {
            'section_80c': self.user.get('deduction_80c', 0),  # Up to 1.5L
            'section_80d': self.user.get('deduction_80d', 0),  # Health insurance
            'section_80e': self.user.get('deduction_80e', 0),  # Education loan
            'section_80g': self.user.get('deduction_80g', 0),  # Donations
            'section_80tta': self.user.get('deduction_80tta', 0),  # Interest on savings
            'hra': self.user.get('hra_deduction', 0),  # House Rent Allowance
            'standard_deduction': 50000,  # Standard deduction for salaried
            'total': sum([
                self.user.get('deduction_80c', 0),
                self.user.get('deduction_80d', 0),
                self.user.get('deduction_80e', 0),
                self.user.get('deduction_80g', 0),
                self.user.get('deduction_80tta', 0),
                self.user.get('hra_deduction', 0),
                50000  # Standard deduction
            ])
        }
    
    def calculate_tax_new_regime(self, taxable_income: float) -> Dict:
        """Calculate tax under new regime (FY 2024-25)"""
        tax_slabs = [
            (0, 300000, 0),      # Up to 3L: 0%
            (300000, 700000, 5),  # 3L-7L: 5%
            (700000, 1000000, 10), # 7L-10L: 10%
            (1000000, 1200000, 15), # 10L-12L: 15%
            (1200000, 1500000, 20), # 12L-15L: 20%
            (1500000, float('inf'), 30)  # Above 15L: 30%
        ]
        
        tax = 0
        remaining = taxable_income
        
        for i, (lower, upper, rate) in enumerate(tax_slabs):
            if remaining <= 0:
                break
            if i == len(tax_slabs) - 1:
                tax += remaining * rate / 100
                break
            if remaining > upper - lower:
                tax += (upper - lower) * rate / 100
                remaining -= (upper - lower)
            else:
                tax += remaining * rate / 100
                remaining = 0
        
        # Rebate under section 87A (up to 7L income)
        if taxable_income <= 700000:
            tax = max(0, tax - 25000)
        
        # Health and Education Cess (4%)
        cess = tax * 0.04
        
        return {
            'base_tax': round(tax, 2),
            'cess': round(cess, 2),
            'total_tax': round(tax + cess, 2),
            'effective_rate': round((tax + cess) / taxable_income * 100, 2) if taxable_income > 0 else 0
        }
    
    def calculate_tax_old_regime(self, taxable_income: float) -> Dict:
        """Calculate tax under old regime"""
        tax_slabs = [
            (0, 250000, 0),      # Up to 2.5L: 0%
            (250000, 500000, 5),  # 2.5L-5L: 5%
            (500000, 1000000, 20), # 5L-10L: 20%
            (1000000, float('inf'), 30)  # Above 10L: 30%
        ]
        
        tax = 0
        remaining = taxable_income
        
        for i, (lower, upper, rate) in enumerate(tax_slabs):
            if remaining <= 0:
                break
            if i == len(tax_slabs) - 1:
                tax += remaining * rate / 100
                break
            if remaining > upper - lower:
                tax += (upper - lower) * rate / 100
                remaining -= (upper - lower)
            else:
                tax += remaining * rate / 100
                remaining = 0
        
        # Rebate under section 87A (up to 5L income)
        if taxable_income <= 500000:
            tax = max(0, tax - 12500)
        
        # Health and Education Cess (4%)
        cess = tax * 0.04
        
        return {
            'base_tax': round(tax, 2),
            'cess': round(cess, 2),
            'total_tax': round(tax + cess, 2),
            'effective_rate': round((tax + cess) / taxable_income * 100, 2) if taxable_income > 0 else 0
        }
    def calculate_tax(self) -> Dict:
        """Calculate tax liability"""
        gross_total = self.income['total']
        total_deductions = self.deductions['total']

        # Old regime allows all deductions (80C, 80D, 80E, 80G, 80TTA, HRA,
        # standard deduction).
        old_regime_taxable_income = max(0, gross_total - total_deductions)

        # New regime disallows most deductions - only the standard
        # deduction applies. Using total_deductions here would leak
        # old-regime-only deductions into the new regime calculation and
        # understate new regime tax.
        new_regime_deductions = self.deductions.get('standard_deduction', 50000)
        new_regime_taxable_income = max(0, gross_total - new_regime_deductions)

        # Calculate under both regimes
        new_regime = self.calculate_tax_new_regime(new_regime_taxable_income)
        old_regime = self.calculate_tax_old_regime(old_regime_taxable_income)
        
        # Determine recommended regime
        recommended = 'new' if new_regime['total_tax'] <= old_regime['total_tax'] else 'old'
        
        return {
            'gross_total_income': gross_total,
            'total_deductions': total_deductions,
            'taxable_income': {
                'new_regime': new_regime_taxable_income,
                'old_regime': old_regime_taxable_income
            },
            'new_regime': new_regime,
            'old_regime': old_regime,
            'recommended_regime': recommended,
            'savings': round(abs(new_regime['total_tax'] - old_regime['total_tax']), 2),
            'tax_refund': max(0, self.user.get('tds', 0) - new_regime['total_tax'])
        }
    
    def generate_itr(self, form_type: str = 'ITR-1') -> Dict:
        """
        Generate ITR form
        
        Args:
            form_type: ITR-1, ITR-2, or ITR-3
        
        Returns:
            Dict with complete ITR data
        """
        tax_result = self.calculate_tax()
        
        # Determine which ITR form is applicable
        if form_type == 'auto':
            form_type = self._detect_itr_type()
        
        itr_data = {
            'form_type': form_type,
            'assessment_year': datetime.now().year,
            'financial_year': datetime.now().year - 1,
            'personal_info': {
                'name': self.user.get('name', ''),
                'pan': self.user.get('pan', ''),
                'aadhar': self.user.get('aadhar', ''),
                'dob': self.user.get('dob', ''),
                'email': self.user.get('email', ''),
                'mobile': self.user.get('mobile', ''),
                'address': self.user.get('address', '')
            },
            'income': self.income,
            'deductions': self.deductions,
            'tax_calculation': tax_result,
            'tax_payments': {
                'tds': self.user.get('tds', 0),
                'advance_tax': self.user.get('advance_tax', 0),
                'self_assessment': self.user.get('self_assessment_tax', 0)
            },
            'bank_details': {
                'account_number': self.user.get('bank_account', ''),
                'ifsc_code': self.user.get('ifsc', ''),
                'account_type': self.user.get('account_type', 'savings')
            },
            'signature': self.user.get('signature', ''),
            'generated_at': datetime.now().isoformat()
        }
        
        return itr_data
    
    def _detect_itr_type(self) -> str:
        """Detect which ITR form is applicable"""
        # ITR-1: Only salary/pension/family pension income
        if self.income['business'] == 0 and self.income['capital_gains'] == 0:
            return 'ITR-1'
        # ITR-2: Capital gains, multiple house properties
        elif self.income['business'] == 0 and self.income['capital_gains'] > 0:
            return 'ITR-2'
        # ITR-3: Business/profession income
        else:
            return 'ITR-3'
    
    def parse_form16(self, pdf_path: str) -> Dict:
        """
        Parse Form 16 PDF to extract data
        
        Args:
            pdf_path: Path to Form 16 PDF
        
        Returns:
            Dict with extracted data
        """
        try:
            data = {
                'success': True,
                'employer': '',
                'pan': '',
                'salary': 0,
                'tds': 0,
                'deductions_80c': 0,
                'deductions_80d': 0,
                'hra': 0,
                'standard_deduction': 0
            }
            
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page in pdf.pages:
                    text += page.extract_text() or ''
            
            # Extract employer name
            emp_match = re.search(r'Employer\s*[:\-]?\s*([A-Za-z0-9\s&,\.]+)', text, re.IGNORECASE)
            if emp_match:
                data['employer'] = emp_match.group(1).strip()
            
            # Extract PAN
            pan_match = re.search(r'PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])', text, re.IGNORECASE)
            if pan_match:
                data['pan'] = pan_match.group(1)
            
            # Extract salary
            salary_patterns = [
                r'(?:Gross\s*Salary|Salary)\s*[:\-]?\s*[₹Rs\.\s]*([\d,]+\.?\d*)',
                r'(?:Total\s*Income)\s*[:\-]?\s*[₹Rs\.\s]*([\d,]+\.?\d*)'
            ]
            for pattern in salary_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['salary'] = float(match.group(1).replace(',', ''))
                    break
            
            # Extract TDS
            tds_match = re.search(r'TDS\s*[:\-]?\s*[₹Rs\.\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if tds_match:
                data['tds'] = float(tds_match.group(1).replace(',', ''))
            
            # Extract 80C deductions
            sec80c_match = re.search(r'80C\s*[:\-]?\s*[₹Rs\.\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if sec80c_match:
                data['deductions_80c'] = float(sec80c_match.group(1).replace(',', ''))
            
            return data
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_tax_saving_recommendations(self) -> List[Dict]:
        """Get personalized tax saving recommendations"""
        recommendations = []
        tax_result = self.calculate_tax()
        
        # Check 80C utilization
        used_80c = self.deductions.get('section_80c', 0)
        limit_80c = 150000
        if used_80c < limit_80c:
            remaining = limit_80c - used_80c
            recommendations.append({
                'section': '80C',
                'limit': limit_80c,
                'used': used_80c,
                'remaining': remaining,
                'suggestion': f'Invest ₹{remaining:,.2f} in ELSS, PPF, or Tax-saving FD to save tax',
                'priority': 'high'
            })
        
        # Check 80D (Health Insurance)
        used_80d = self.deductions.get('section_80d', 0)
        limit_80d = 25000
        if used_80d < limit_80d:
            remaining = limit_80d - used_80d
            recommendations.append({
                'section': '80D',
                'limit': limit_80d,
                'used': used_80d,
                'remaining': remaining,
                'suggestion': f'Buy health insurance of ₹{remaining:,.2f} to save tax',
                'priority': 'medium'
            })
        
        # Check NPS (Section 80CCD)
        used_nps = self.deductions.get('section_80ccd', 0)
        limit_nps = 50000
        if used_nps < limit_nps:
            remaining = limit_nps - used_nps
            recommendations.append({
                'section': '80CCD(1B)',
                'limit': limit_nps,
                'used': used_nps,
                'remaining': remaining,
                'suggestion': f'Invest ₹{remaining:,.2f} in NPS for additional tax benefit',
                'priority': 'medium'
            })
        
        return recommendations
    
    def get_filing_status(self) -> Dict:
        """Get tax filing status"""
        tax_result = self.calculate_tax()
        payment_due_income = tax_result['taxable_income'][f"{tax_result['recommended_regime']}_regime"]
        return {
            'status': 'pending',
            'last_filed': self.user.get('last_filed', None),
            'pending_refund': self.user.get('pending_refund', 0),
            'payment_due': payment_due_income > 0
        }