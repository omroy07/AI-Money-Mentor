"""
Advanced Financial Ratio Analysis Dashboard
Comprehensive financial health analysis with industry benchmarks
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json


class FinancialRatioAnalyzer:
    """
    Comprehensive Financial Ratio Analysis Engine
    """
    
    # Ratios where a LOWER value than the benchmark is actually better
    LOWER_IS_BETTER = {'debt_to_equity', 'debt_ratio'}
    
    def __init__(self, financial_data: Dict):
        """
        Initialize with financial data
        
        Args:
            financial_data: Dict with financial metrics
        """
        self.data = financial_data
        self._validate_data()
    
    def _validate_data(self):
        """Validate required fields"""
        required = ['current_assets', 'current_liabilities', 'total_assets', 
                   'total_liabilities', 'equity', 'revenue', 'net_income']
        for field in required:
            if field not in self.data:
                self.data[field] = 0
    
    def calculate_liquidity_ratios(self) -> Dict:
        """Calculate liquidity ratios"""
        ca = self.data.get('current_assets', 0)
        cl = self.data.get('current_liabilities', 1)
        inventory = self.data.get('inventory', 0)
        cash = self.data.get('cash', 0)
        
        return {
            'current_ratio': round(ca / cl if cl > 0 else 0, 2),
            'quick_ratio': round((ca - inventory) / cl if cl > 0 else 0, 2),
            'cash_ratio': round(cash / cl if cl > 0 else 0, 2)
        }
    
    def calculate_solvency_ratios(self) -> Dict:
        """Calculate solvency ratios"""
        tl = self.data.get('total_liabilities', 0)
        equity = self.data.get('equity', 1)
        ebit = self.data.get('ebit', 0)
        interest = self.data.get('interest_expense', 1)
        ta = self.data.get('total_assets', 1)
        
        return {
            'debt_to_equity': round(tl / equity if equity > 0 else 0, 2),
            'interest_coverage': round(ebit / interest if interest > 0 else 0, 2),
            'debt_ratio': round(tl / ta if ta > 0 else 0, 2)
        }
    
    def calculate_efficiency_ratios(self) -> Dict:
        """Calculate efficiency ratios"""
        revenue = self.data.get('revenue', 0)
        ta = self.data.get('total_assets', 1)
        inventory = self.data.get('inventory', 0)
        cogs = self.data.get('cogs', 1)
        
        return {
            'asset_turnover': round(revenue / ta if ta > 0 else 0, 2),
            'inventory_turnover': round(cogs / inventory if inventory > 0 else 0, 2),
            'receivables_turnover': round(revenue / self.data.get('receivables', 1) if self.data.get('receivables', 0) > 0 else 0, 2)
        }
    
    def calculate_profitability_ratios(self) -> Dict:
        """Calculate profitability ratios"""
        revenue = self.data.get('revenue', 1)
        net_income = self.data.get('net_income', 0)
        ebit = self.data.get('ebit', 0)
        ta = self.data.get('total_assets', 1)
        equity = self.data.get('equity', 1)
        
        return {
            'gross_margin': round((revenue - self.data.get('cogs', 0)) / revenue * 100 if revenue > 0 else 0, 2),
            'net_margin': round(net_income / revenue * 100 if revenue > 0 else 0, 2),
            'roi': round(ebit / ta * 100 if ta > 0 else 0, 2),
            'roe': round(net_income / equity * 100 if equity > 0 else 0, 2)
        }
    
    def get_peer_comparison(self, industry: str = 'general') -> Dict:
        """Get peer comparison with industry benchmarks"""
        benchmarks = self._get_benchmarks(industry)
        
        current = {
            'liquidity': self.calculate_liquidity_ratios(),
            'solvency': self.calculate_solvency_ratios(),
            'efficiency': self.calculate_efficiency_ratios(),
            'profitability': self.calculate_profitability_ratios()
        }
        
        comparison = {}
        for category, ratios in current.items():
            comparison[category] = {}
            for ratio, value in ratios.items():
                benchmark = benchmarks.get(category, {}).get(ratio, 0)
                comparison[category][ratio] = {
                    'your_value': value,
                    'benchmark': benchmark,
                    'difference': round(value - benchmark, 2),
                    'status': self._get_status(value, benchmark, ratio)
                }
        
        return {
            'current': current,
            'comparison': comparison,
            'industry': industry,
            'overall_health': self._get_overall_health(comparison)
        }
    
    def _get_benchmarks(self, industry: str) -> Dict:
        """Get industry benchmarks"""
        benchmarks = {
            'general': {
                'liquidity': {'current_ratio': 1.5, 'quick_ratio': 1.0, 'cash_ratio': 0.3},
                'solvency': {'debt_to_equity': 1.0, 'interest_coverage': 3.0, 'debt_ratio': 0.5},
                'efficiency': {'asset_turnover': 1.0, 'inventory_turnover': 4.0, 'receivables_turnover': 6.0},
                'profitability': {'gross_margin': 30.0, 'net_margin': 10.0, 'roi': 8.0, 'roe': 15.0}
            },
            'tech': {
                'liquidity': {'current_ratio': 1.8, 'quick_ratio': 1.2, 'cash_ratio': 0.5},
                'solvency': {'debt_to_equity': 0.5, 'interest_coverage': 5.0, 'debt_ratio': 0.3},
                'efficiency': {'asset_turnover': 0.8, 'inventory_turnover': 8.0, 'receivables_turnover': 5.0},
                'profitability': {'gross_margin': 50.0, 'net_margin': 15.0, 'roi': 12.0, 'roe': 20.0}
            },
            'finance': {
                'liquidity': {'current_ratio': 1.2, 'quick_ratio': 0.8, 'cash_ratio': 0.2},
                'solvency': {'debt_to_equity': 2.5, 'interest_coverage': 2.0, 'debt_ratio': 0.7},
                'efficiency': {'asset_turnover': 0.2, 'inventory_turnover': 0, 'receivables_turnover': 0},
                'profitability': {'gross_margin': 60.0, 'net_margin': 20.0, 'roi': 10.0, 'roe': 18.0}
            },
            'retail': {
                'liquidity': {'current_ratio': 1.3, 'quick_ratio': 0.6, 'cash_ratio': 0.2},
                'solvency': {'debt_to_equity': 1.5, 'interest_coverage': 2.5, 'debt_ratio': 0.6},
                'efficiency': {'asset_turnover': 2.0, 'inventory_turnover': 6.0, 'receivables_turnover': 8.0},
                'profitability': {'gross_margin': 25.0, 'net_margin': 5.0, 'roi': 8.0, 'roe': 12.0}
            },
            'healthcare': {
                'liquidity': {'current_ratio': 1.6, 'quick_ratio': 1.0, 'cash_ratio': 0.4},
                'solvency': {'debt_to_equity': 0.8, 'interest_coverage': 4.0, 'debt_ratio': 0.4},
                'efficiency': {'asset_turnover': 0.6, 'inventory_turnover': 5.0, 'receivables_turnover': 4.0},
                'profitability': {'gross_margin': 40.0, 'net_margin': 12.0, 'roi': 10.0, 'roe': 16.0}
            },
            'real_estate': {
                'liquidity': {'current_ratio': 1.0, 'quick_ratio': 0.5, 'cash_ratio': 0.1},
                'solvency': {'debt_to_equity': 2.0, 'interest_coverage': 2.0, 'debt_ratio': 0.6},
                'efficiency': {'asset_turnover': 0.1, 'inventory_turnover': 0, 'receivables_turnover': 0},
                'profitability': {'gross_margin': 35.0, 'net_margin': 15.0, 'roi': 8.0, 'roe': 15.0}
            },
            'manufacturing': {
                'liquidity': {'current_ratio': 1.4, 'quick_ratio': 0.8, 'cash_ratio': 0.2},
                'solvency': {'debt_to_equity': 1.2, 'interest_coverage': 3.0, 'debt_ratio': 0.5},
                'efficiency': {'asset_turnover': 1.0, 'inventory_turnover': 4.0, 'receivables_turnover': 5.0},
                'profitability': {'gross_margin': 30.0, 'net_margin': 8.0, 'roi': 10.0, 'roe': 14.0}
            },
            'energy': {
                'liquidity': {'current_ratio': 1.0, 'quick_ratio': 0.6, 'cash_ratio': 0.2},
                'solvency': {'debt_to_equity': 1.8, 'interest_coverage': 2.5, 'debt_ratio': 0.6},
                'efficiency': {'asset_turnover': 0.5, 'inventory_turnover': 10.0, 'receivables_turnover': 4.0},
                'profitability': {'gross_margin': 20.0, 'net_margin': 8.0, 'roi': 8.0, 'roe': 12.0}
            }
        }
        
        return benchmarks.get(industry, benchmarks['general'])
    

    def _get_status(self, value: float, benchmark: float, ratio_key: str = None) -> str:
        """Get status based on comparison with benchmark"""
        if benchmark == 0:
            return 'neutral'
        
        diff = value - benchmark

        # For ratios where lower is better (leverage/debt ratios), invert the
        # comparison so that being below benchmark counts as "excellent"/"good".
        if ratio_key in self.LOWER_IS_BETTER:
            diff = -diff

        # For ratios where higher is better
        if diff >= 0.2 * benchmark:
            return 'excellent'
        elif diff >= 0:
            return 'good'
        elif diff >= -0.2 * benchmark:
            return 'fair'
        else:
            return 'poor'
    def _get_overall_health(self, comparison: Dict) -> Dict:
        """Calculate overall financial health score"""
        scores = []
        total_ratios = 0
        
        for category, ratios in comparison.items():
            for ratio, data in ratios.items():
                status_weights = {'excellent': 100, 'good': 80, 'fair': 60, 'poor': 30, 'neutral': 50}
                scores.append(status_weights.get(data['status'], 50))
                total_ratios += 1
        
        if total_ratios == 0:
            avg_score = 0
        else:
            avg_score = sum(scores) / total_ratios
        
        if avg_score >= 80:
            grade = 'A'
            description = 'Excellent financial health'
        elif avg_score >= 65:
            grade = 'B'
            description = 'Good financial health'
        elif avg_score >= 50:
            grade = 'C'
            description = 'Average financial health'
        else:
            grade = 'D'
            description = 'Needs improvement'
        
        return {
            'score': round(avg_score, 1),
            'grade': grade,
            'description': description,
            'total_ratios': total_ratios
        }
    
    def get_all_ratios(self) -> Dict:
        """Get all calculated ratios in one dict"""
        return {
            'liquidity': self.calculate_liquidity_ratios(),
            'solvency': self.calculate_solvency_ratios(),
            'efficiency': self.calculate_efficiency_ratios(),
            'profitability': self.calculate_profitability_ratios()
        }
    
    def generate_report(self, industry: str = 'general') -> Dict:
        """Generate comprehensive ratio analysis report"""
        all_ratios = self.get_all_ratios()
        comparison = self.get_peer_comparison(industry)
        
        # Find strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for category, ratios in comparison['comparison'].items():
            for ratio, data in ratios.items():
                if data['status'] in ['excellent', 'good']:
                    strengths.append({
                        'category': category,
                        'ratio': ratio,
                        'value': data['your_value'],
                        'benchmark': data['benchmark']
                    })
                elif data['status'] in ['poor']:
                    weaknesses.append({
                        'category': category,
                        'ratio': ratio,
                        'value': data['your_value'],
                        'benchmark': data['benchmark'],
                        'suggestion': self._get_suggestion(category, ratio)
                    })
        
        return {
            'ratios': all_ratios,
            'comparison': comparison,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'overall_health': comparison['overall_health'],
            'generated_at': datetime.now().isoformat(),
            'industry': industry
        }
    
    def _get_suggestion(self, category: str, ratio: str) -> str:
        """Get improvement suggestions for weak ratios"""
        suggestions = {
            'liquidity': {
                'current_ratio': 'Increase current assets or reduce short-term liabilities',
                'quick_ratio': 'Improve liquid asset position, reduce inventory',
                'cash_ratio': 'Maintain adequate cash reserves'
            },
            'solvency': {
                'debt_to_equity': 'Reduce debt or increase equity capital',
                'interest_coverage': 'Improve operating income or reduce interest costs',
                'debt_ratio': 'Reduce total liabilities or increase assets'
            },
            'efficiency': {
                'asset_turnover': 'Improve revenue generation from existing assets',
                'inventory_turnover': 'Optimize inventory management',
                'receivables_turnover': 'Improve collection efficiency'
            },
            'profitability': {
                'gross_margin': 'Reduce COGS or increase prices',
                'net_margin': 'Control operating expenses',
                'roi': 'Improve return on investments',
                'roe': 'Increase profitability or optimize capital structure'
            }
        }
        return suggestions.get(category, {}).get(ratio, 'Review and improve this metric')