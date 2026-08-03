"""
FIRE (Financial Independence) Path Planner with Monte Carlo Simulation
Advanced retirement planning with probabilistic modeling
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import warnings
warnings.filterwarnings('ignore')


class FIREPlanner:
    """
    Financial Independence Retire Early (FIRE) Path Planner
    Uses Monte Carlo simulation for robust retirement planning
    """
    
    def __init__(
        self,
        current_age: int,
        retirement_age: int,
        annual_expenses: float,
        current_corpus: float,
        monthly_savings: float = 0,
        return_mean: float = 0.10,
        return_std: float = 0.15,
        inflation_rate: float = 0.06,
        withdrawal_rate: float = 0.04,
        life_expectancy: int = 85
    ):
        """
        Initialize FIRE Planner
        
        Args:
            current_age: Current age
            retirement_age: Target retirement age
            annual_expenses: Current annual expenses
            current_corpus: Current retirement corpus
            monthly_savings: Monthly savings until retirement
            return_mean: Expected annual return mean
            return_std: Expected annual return standard deviation
            inflation_rate: Expected inflation rate
            withdrawal_rate: Safe withdrawal rate (4% rule)
            life_expectancy: Expected lifespan
        """
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.annual_expenses = annual_expenses
        self.current_corpus = current_corpus
        self.monthly_savings = monthly_savings
        self.return_mean = return_mean
        self.return_std = return_std
        self.inflation_rate = inflation_rate
        self.withdrawal_rate = withdrawal_rate
        self.life_expectancy = life_expectancy

        # Derived values
        self.years_to_retirement = retirement_age - current_age
        self.retirement_years = life_expectancy - retirement_age
        self.target_corpus = annual_expenses * (1 / withdrawal_rate) if withdrawal_rate > 0 else annual_expenses * 25
        self.yearly_savings = monthly_savings * 12

    def compute_lean_fat_projections(self) -> Dict:
        """
        Compute Lean / Regular / Fat FIRE corpus targets.

        The "Lean FIRE" and "Fat FIRE" terminology describes how lavish the
        post-retirement lifestyle is expected to be:

          - Lean FIRE   = corpus needed to fund 50% of current annual expenses
          - Regular     = corpus needed at the configured withdrawal rate
                          (default 4% rule, i.e. 25x annual expenses)
          - Fat FIRE    = corpus needed to fund 150% of current annual expenses

        All numbers are *today's-rupee* targets — the planner already applies
        inflation to the simulator itself, so we leave these as constant
        nominal anchors and let the time-series projection handle the
        compounded growth/decay story.

        Returns:
            Dict with the three corpus targets and their implied multiplier.
        """
        multiplier = 1.0 / self.withdrawal_rate if self.withdrawal_rate > 0 else 25.0
        regular = self.annual_expenses * multiplier
        return {
            'lean': {
                'name': 'Lean FIRE',
                'annual_expenses': round(self.annual_expenses * 0.5, 2),
                'target_corpus': round(regular * 0.5, 2),
                'multiplier_of_expenses': round(multiplier * 0.5, 2),
                'description': 'Minimalist retirement — 50% of current expenses, no frills',
            },
            'regular': {
                'name': 'Regular FIRE',
                'annual_expenses': round(self.annual_expenses, 2),
                'target_corpus': round(regular, 2),
                'multiplier_of_expenses': round(multiplier, 2),
                'description': f'Maintain current lifestyle at the {self.withdrawal_rate:.1%} withdrawal rate',
            },
            'fat': {
                'name': 'Fat FIRE',
                'annual_expenses': round(self.annual_expenses * 1.5, 2),
                'target_corpus': round(regular * 1.5, 2),
                'multiplier_of_expenses': round(multiplier * 1.5, 2),
                'description': 'Lavish retirement — 150% of current expenses, travel + hobbies',
            },
        }

    def get_timeline_projection(self, iterations: int = 200) -> Dict:
        """
        Compute a year-by-year time series that traces both the accumulation
        phase (current_age → retirement_age) and the decumulation phase
        (retirement_age → life_expectancy).

        For each calendar year we aggregate the simulation paths into 5th /
        25th / 50th (median) / 75th / 95th percentiles. The phase column lets
        the UI colour the chart and compute the "when does the corpus hit
        zero" line.

        Args:
            iterations: Monte Carlo iterations used to populate the percentile
                        bands. 200 keeps the route under ~1s on commodity
                        hardware; tests pin it lower.

        Returns:
            Dict with `ages`, `phases`, `percentiles`, `median_path`,
            `depletion_age` and the `target_corpus` reference line.
        """
        mc_results = self.run_monte_carlo(iterations=iterations)
        paths = mc_results['all_paths']

        total_years = self.years_to_retirement + self.retirement_years
        ages = [self.current_age + offset for offset in range(total_years)]

        # Per-year percentile bands across all paths.
        # Each path may have stopped early (corpus depleted) — pad with 0.
        per_year_arrays: List[List[float]] = [[] for _ in range(total_years)]
        for path in paths:
            portfolio = path['portfolio']
            for offset, value in enumerate(portfolio):
                per_year_arrays[offset].append(max(value, 0.0))

        percentiles_by_year: Dict[str, List[float]] = {
            '5th': [],
            '25th': [],
            '50th': [],
            '75th': [],
            '95th': [],
        }
        for year_values in per_year_arrays:
            if not year_values:
                for key in percentiles_by_year:
                    percentiles_by_year[key].append(0.0)
                continue
            arr = np.array(year_values, dtype=float)
            p5, p25, p50, p75, p95 = np.percentile(arr, [5, 25, 50, 75, 95])
            percentiles_by_year['5th'].append(round(float(p5), 2))
            percentiles_by_year['25th'].append(round(float(p25), 2))
            percentiles_by_year['50th'].append(round(float(p50), 2))
            percentiles_by_year['75th'].append(round(float(p75), 2))
            percentiles_by_year['95th'].append(round(float(p95), 2))

        median_path = percentiles_by_year['50th']

        # Phase label per year: 'accumulation' until retirement_age (incl.),
        # 'retirement' thereafter.
        phases = []
        for age in ages:
            if age < self.retirement_age:
                phases.append('accumulation')
            else:
                phases.append('retirement')

        # Depletion age — first year where the 50th percentile hits zero
        # during retirement. None if the corpus never depletes.
        depletion_age = None
        for idx, phase in enumerate(phases):
            if phase != 'retirement':
                continue
            if median_path[idx] <= 0:
                depletion_age = ages[idx]
                break

        # Target corpus reference line for the chart — drawn against today's
        # nominal rupee. The chart can overlay inflation-adjusted variants if
        # it wants.
        target_reference = [round(self.target_corpus, 2)] * total_years

        return {
            'ages': ages,
            'phases': phases,
            'percentiles': percentiles_by_year,
            'median_path': median_path,
            'target_corpus': round(self.target_corpus, 2),
            'target_reference_line': target_reference,
            'depletion_age': depletion_age,
            'retirement_age': self.retirement_age,
            'life_expectancy': self.life_expectancy,
            'iterations': iterations,
            'success_probability': mc_results['success']['probability'],
        }

    def run_monte_carlo(self, iterations: int = 1000) -> Dict:
        """
        Run Monte Carlo simulation for FIRE planning
        
        Args:
            iterations: Number of simulation iterations
        
        Returns:
            Dict with simulation results
        """
        results = []
        final_corpuses = []
        success_paths = []
        fail_paths = []
        
        for i in range(iterations):
            result = self._simulate_path()
            results.append(result)
            final_corpuses.append(result['final_corpus'])
            
            if result['success']:
                success_paths.append(result['portfolio'])
            else:
                fail_paths.append(result['portfolio'])
        
        # Calculate statistics
        success_count = sum(1 for r in results if r['success'])
        success_probability = (success_count / iterations) * 100
        
        # Calculate percentiles
        percentiles = np.percentile(final_corpuses, [5, 25, 50, 75, 95])
        
        # Find best and worst paths
        best_path_index = np.argmax(final_corpuses)
        worst_path_index = np.argmin(final_corpuses)
        
        return {
            'success': {
                'count': success_count,
                'probability': round(success_probability, 2),
                'total': iterations
            },
            'corpus': {
                'mean': round(np.mean(final_corpuses), 2),
                'median': round(np.median(final_corpuses), 2),
                'std': round(np.std(final_corpuses), 2),
                'min': round(np.min(final_corpuses), 2),
                'max': round(np.max(final_corpuses), 2),
                'percentiles': {
                    '5th': round(percentiles[0], 2),
                    '25th': round(percentiles[1], 2),
                    '50th': round(percentiles[2], 2),
                    '75th': round(percentiles[3], 2),
                    '95th': round(percentiles[4], 2)
                }
            },
            'best_path': {
                'final_corpus': round(final_corpuses[best_path_index], 2),
                'portfolio': success_paths[best_path_index] if best_path_index < len(success_paths) else []
            },
            'worst_path': {
                'final_corpus': round(final_corpuses[worst_path_index], 2),
                'portfolio': fail_paths[worst_path_index] if worst_path_index < len(fail_paths) else []
            },
            'all_paths': results,
            'all_corpuses': final_corpuses,
            'success_paths': success_paths,
            'fail_paths': fail_paths
        }
    
    def _simulate_path(self) -> Dict:
        """
        Simulate a single retirement path
        
        Returns:
            Dict with path results
        """
        years_to_retirement = self.years_to_retirement
        retirement_years = self.retirement_years
        
        # Pre-retirement phase
        corpus = self.current_corpus
        pre_retirement_portfolio = []
        
        for year in range(years_to_retirement):
            # Random annual return
            return_rate = np.random.normal(self.return_mean, self.return_std)
            corpus *= (1 + return_rate)
            
            # Add monthly savings
            corpus += self.yearly_savings
            
            # Adjust for inflation (expenses increase)
            if year > 0:
                corpus -= self.annual_expenses * (1 + self.inflation_rate) ** year * 0.1  # Living expenses during working years
            
            pre_retirement_portfolio.append(corpus)
        
        # Retirement phase
        retirement_portfolio = []
        expenses = self.annual_expenses
        
        for year in range(retirement_years):
            # Random annual return
            return_rate = np.random.normal(self.return_mean, self.return_std)
            corpus *= (1 + return_rate)
            
            # Withdraw expenses (adjusted for inflation)
            expenses_at_year = expenses * (1 + self.inflation_rate) ** year
            corpus -= expenses_at_year
            
            retirement_portfolio.append(corpus)
            
            # Stop if corpus is depleted
            if corpus <= 0:
                break
        
        # Determine if path was successful
        success = corpus > 0 and len(retirement_portfolio) == retirement_years
        
        return {
            'success': success,
            'pre_retirement_portfolio': pre_retirement_portfolio,
            'retirement_portfolio': retirement_portfolio,
            'portfolio': pre_retirement_portfolio + retirement_portfolio,
            'final_corpus': corpus,
            'years_successful': len(retirement_portfolio),
            'retirement_years': retirement_years
        }
    
    def calculate_withdrawal_strategy(self) -> Dict:
        """
        Calculate optimal withdrawal strategy
        
        Returns:
            Dict with withdrawal strategy details
        """
        strategies = {
            'fixed_4_percent': {
                'name': 'Fixed 4% Rule',
                'withdrawal_amount': self.annual_expenses * 0.04,
                'description': 'Withdraw 4% of initial portfolio annually, adjusted for inflation'
            },
            'dynamic_4_percent': {
                'name': 'Dynamic 4% Rule',
                'withdrawal_amount': self.annual_expenses * 0.04,
                'description': 'Withdraw 4% of current portfolio value each year'
            },
            'fixed_income': {
                'name': 'Fixed Income Strategy',
                'withdrawal_amount': self.annual_expenses,
                'description': 'Withdraw fixed annual expenses (not adjusted for inflation)'
            },
            'income_smoothing': {
                'name': 'Income Smoothing',
                'withdrawal_amount': self.annual_expenses * 0.035,
                'description': 'Lower initial withdrawal (3.5%) with higher safety margin'
            }
        }
        
        # Simulate each strategy
        results = {}
        for key, strategy in strategies.items():
            # Run quick Monte Carlo for each strategy
            original_withdrawal = self.withdrawal_rate
            self.withdrawal_rate = strategy['withdrawal_amount'] / self.annual_expenses if self.annual_expenses > 0 else 0.04
            sim_results = self.run_monte_carlo(iterations=200)
            self.withdrawal_rate = original_withdrawal
            
            results[key] = {
                'name': strategy['name'],
                'description': strategy['description'],
                'withdrawal_amount': round(strategy['withdrawal_amount'], 2),
                'success_probability': sim_results['success']['probability']
            }
        
        return {
            'strategies': results,
            'recommended': max(results.items(), key=lambda x: x[1]['success_probability'])[0]
        }
    
    def sensitivity_analysis(self) -> Dict:
        """
        Analyze sensitivity to key variables
        
        Returns:
            Dict with sensitivity results
        """
        variables = {
            'return_rate': {
                'values': [0.06, 0.08, 0.10, 0.12, 0.14],
                'current': self.return_mean,
                'label': 'Expected Return Rate'
            },
            'savings_rate': {
                'values': [0.5, 0.75, 1.0, 1.25, 1.5],
                'current': 1.0,
                'label': 'Monthly Savings Multiplier'
            },
            'withdrawal_rate': {
                'values': [0.03, 0.035, 0.04, 0.045, 0.05],
                'current': self.withdrawal_rate,
                'label': 'Withdrawal Rate'
            },
            'retirement_age': {
                'values': [self.retirement_age - 5, self.retirement_age - 2, self.retirement_age, self.retirement_age + 2, self.retirement_age + 5],
                'current': self.retirement_age,
                'label': 'Retirement Age'
            }
        }
        
        results = {}
        for var_name, var_data in variables.items():
            var_results = []
            for value in var_data['values']:
                # Create temporary planner with modified value
                if var_name == 'return_rate':
                    temp_planner = FIREPlanner(
                        self.current_age,
                        self.retirement_age,
                        self.annual_expenses,
                        self.current_corpus,
                        self.monthly_savings,
                        return_mean=value,
                        return_std=self.return_std,
                        inflation_rate=self.inflation_rate,
                        withdrawal_rate=self.withdrawal_rate
                    )
                elif var_name == 'savings_rate':
                    temp_planner = FIREPlanner(
                        self.current_age,
                        self.retirement_age,
                        self.annual_expenses,
                        self.current_corpus,
                        self.monthly_savings * value,
                        return_mean=self.return_mean,
                        return_std=self.return_std,
                        inflation_rate=self.inflation_rate,
                        withdrawal_rate=self.withdrawal_rate
                    )
                elif var_name == 'withdrawal_rate':
                    temp_planner = FIREPlanner(
                        self.current_age,
                        self.retirement_age,
                        self.annual_expenses,
                        self.current_corpus,
                        self.monthly_savings,
                        return_mean=self.return_mean,
                        return_std=self.return_std,
                        inflation_rate=self.inflation_rate,
                        withdrawal_rate=value
                    )
                elif var_name == 'retirement_age':
                    temp_planner = FIREPlanner(
                        self.current_age,
                        int(value),
                        self.annual_expenses,
                        self.current_corpus,
                        self.monthly_savings,
                        return_mean=self.return_mean,
                        return_std=self.return_std,
                        inflation_rate=self.inflation_rate,
                        withdrawal_rate=self.withdrawal_rate
                    )
                else:
                    continue
                
                sim_result = temp_planner.run_monte_carlo(iterations=200)
                var_results.append({
                    'value': value,
                    'success_probability': sim_result['success']['probability'],
                    'median_corpus': sim_result['corpus']['median']
                })
            
            results[var_name] = {
                'label': var_data['label'],
                'current_value': var_data['current'],
                'results': var_results,
                'sensitivity': self._calculate_sensitivity(var_results)
            }
        
        return results
    
    def _calculate_sensitivity(self, results: List[Dict]) -> Dict:
        """Calculate sensitivity metrics"""
        if len(results) < 2:
            return {'impact': 'low', 'description': 'Insufficient data'}
        
        values = [r['value'] for r in results]
        probabilities = [r['success_probability'] for r in results]
        
        # Calculate correlation
        correlation = np.corrcoef(values, probabilities)[0, 1] if len(values) > 1 else 0
        
        # Calculate impact range
        impact_range = max(probabilities) - min(probabilities)
        
        impact_level = 'high' if impact_range > 20 else 'medium' if impact_range > 10 else 'low'
        
        return {
            'correlation': round(correlation, 3),
            'impact_range': round(impact_range, 2),
            'impact_level': impact_level,
            'description': f"Changing this variable by ±25% changes success probability by {impact_range:.1f}%"
        }
    
    def generate_optimization_recommendations(self) -> Dict:
        """
        Generate recommendations to improve FIRE success probability
        
        Returns:
            Dict with optimization recommendations
        """
        # Run sensitivity analysis
        sensitivity = self.sensitivity_analysis()
        
        # Find variables with highest impact
        high_impact_vars = []
        for var_name, var_data in sensitivity.items():
            if var_data['sensitivity']['impact_level'] in ['high', 'medium']:
                high_impact_vars.append({
                    'variable': var_name,
                    'label': var_data['label'],
                    'current_value': var_data['current_value'],
                    'impact_level': var_data['sensitivity']['impact_level'],
                    'recommendation': self._get_recommendation(var_name, var_data)
                })
        
        # Sort by impact
        high_impact_vars.sort(key=lambda x: 0 if x['impact_level'] == 'high' else 1)
        
        return {
            'recommendations': high_impact_vars,
            'summary': self._get_summary_recommendation(high_impact_vars)
        }
    
    def _get_recommendation(self, var_name: str, var_data: Dict) -> str:
        """Get specific recommendation for a variable"""
        recommendations = {
            'return_rate': "💡 Consider shifting to a more aggressive investment strategy to increase expected returns, but be aware of higher risk.",
            'savings_rate': "💡 Increase monthly savings by 10-20% to significantly improve success probability.",
            'withdrawal_rate': "💡 Reduce your withdrawal rate from 4% to 3.5% for much higher safety margin.",
            'retirement_age': "💡 Delaying retirement by 2-3 years can dramatically improve success probability."
        }
        return recommendations.get(var_name, "💡 Adjust this variable to optimize your plan.")
    
    def _get_summary_recommendation(self, recommendations: List) -> str:
        """Get summary recommendation"""
        if not recommendations:
            return "Your current plan looks solid! Continue monitoring and adjust as needed."
        
        high_impact_count = sum(1 for r in recommendations if r['impact_level'] == 'high')
        
        if high_impact_count >= 2:
            return "⚠️ Multiple high-impact variables need attention. Consider a comprehensive review of your retirement plan."
        elif high_impact_count == 1:
            return "📊 One high-impact variable identified. Focus on optimizing this first."
        else:
            return "✅ Your plan has manageable risk. Consider fine-tuning for optimal results."
    
    def get_plan_summary(self) -> Dict:
        """
        Get comprehensive plan summary
        
        Returns:
            Dict with plan summary
        """
        # Run Monte Carlo
        mc_results = self.run_monte_carlo(500)
        
        # Calculate withdrawal strategy
        withdrawal_strategy = self.calculate_withdrawal_strategy()
        
        # Sensitivity analysis
        sensitivity = self.sensitivity_analysis()
        
        # Recommendations
        recommendations = self.generate_optimization_recommendations()
        
        return {
            'input_summary': {
                'current_age': self.current_age,
                'retirement_age': self.retirement_age,
                'years_to_retirement': self.years_to_retirement,
                'retirement_years': self.retirement_years,
                'annual_expenses': self.annual_expenses,
                'current_corpus': self.current_corpus,
                'monthly_savings': self.monthly_savings,
                'target_corpus': self.target_corpus,
                'withdrawal_rate': self.withdrawal_rate,
                'life_expectancy': self.life_expectancy,
                'shortfall': round(self.target_corpus - self.current_corpus, 2) if self.target_corpus > self.current_corpus else 0
            },
            'monte_carlo': mc_results,
            'withdrawal_strategy': withdrawal_strategy,
            'sensitivity': sensitivity,
            'recommendations': recommendations,
            'lean_fat_projections': self.compute_lean_fat_projections(),
            'timeline_projection': self.get_timeline_projection(iterations=200),
            'status': self._get_status(mc_results)
        }
    
    def _get_status(self, mc_results: Dict) -> Dict:
        """Get overall plan status"""
        probability = mc_results['success']['probability']
        
        if probability >= 90:
            status = 'excellent'
            message = '🎉 Excellent! Your FIRE plan has a very high probability of success.'
        elif probability >= 70:
            status = 'good'
            message = '✅ Good! Your FIRE plan has a solid chance of success with minor adjustments.'
        elif probability >= 50:
            status = 'fair'
            message = '⚠️ Fair. Your FIRE plan needs optimization to improve success probability.'
        else:
            status = 'poor'
            message = '🔴 Poor. Your FIRE plan needs significant adjustments.'
        
        return {
            'status': status,
            'message': message,
            'probability': probability,
            'confidence': 'high' if probability >= 80 else 'medium' if probability >= 50 else 'low'
        }
    
    def get_visualization_data(self) -> Dict:
        """
        Get data for visualization charts
        
        Returns:
            Dict with chart data
        """
        # Run Monte Carlo
        mc_results = self.run_monte_carlo(500)
        
        # Distribution data
        corpuses = mc_results['all_corpuses']
        hist, bins = np.histogram(corpuses, bins=50)
        
        # Percentile lines
        percentiles = {
            '5th': np.percentile(corpuses, 5),
            '25th': np.percentile(corpuses, 25),
            '50th': np.percentile(corpuses, 50),
            '75th': np.percentile(corpuses, 75),
            '95th': np.percentile(corpuses, 95)
        }
        
        return {
            'distribution': {
                'histogram': hist.tolist(),
                'bins': bins.tolist()
            },
            'percentiles': percentiles,
            'success_probability': mc_results['success']['probability'],
            'best_path': mc_results['best_path'],
            'worst_path': mc_results['worst_path']
        }