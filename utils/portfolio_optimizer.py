"""
Real-Time Portfolio Optimization & Stress Testing Engine
Modern Portfolio Theory implementation for Indian markets
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize, Bounds, LinearConstraint
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class PortfolioOptimizer:
    """
    Advanced Portfolio Optimization Engine
    Implements Modern Portfolio Theory with Indian market context
    """
    
    def __init__(self, holdings: List[Dict], risk_free_rate: float = 0.06):
        """
        Initialize optimizer with portfolio holdings
        
        Args:
            holdings: List of holdings dicts with symbol, quantity, buy_price
            risk_free_rate: Risk-free rate (default 6% for India)
        """
        self.holdings = holdings
        self.risk_free_rate = risk_free_rate
        self.symbols = [h['symbol'] for h in holdings]
        self.prices = [h['current_price'] for h in holdings]
        self.quantities = [h['quantity'] for h in holdings]
        self.current_values = [p * q for p, q in zip(self.prices, self.quantities)]
        self.total_value = sum(self.current_values)
        self.current_weights = [v / self.total_value for v in self.current_values]
        self.returns_data = None
        self.cov_matrix = None
        self.mean_returns = None
        
    def fetch_historical_data(self, period: str = '1y') -> pd.DataFrame:
        """Fetch historical price data for all holdings"""
        data = {}
        for symbol in self.symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                data[symbol] = hist['Close']
            except Exception as e:
                print(f"Could not fetch data for {symbol}: {e}")
                # Use random data for demo if fetch fails
                data[symbol] = self._generate_demo_data()
        
        self.returns_data = pd.DataFrame(data)
        self.returns_data = self.returns_data.fillna(method='ffill')
        
        # Calculate daily returns
        self.returns_data = self.returns_data.pct_change().dropna()
        self.mean_returns = self.returns_data.mean() * 252  # Annualized
        self.cov_matrix = self.returns_data.cov() * 252  # Annualized
        
        return self.returns_data
    
    def _generate_demo_data(self) -> pd.Series:
        """Generate demo data for testing"""
        np.random.seed(42)
        price = 100
        prices = []
        for i in range(252):  # 1 year of trading days
            price *= (1 + np.random.normal(0.0005, 0.02))
            prices.append(price)
        return pd.Series(prices)
    
    def calculate_returns(self) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate mean returns and covariance matrix"""
        if self.returns_data is None:
            self.fetch_historical_data()
        return self.mean_returns, self.cov_matrix
    
    def optimize_portfolio(self, method: str = 'sharpe') -> Dict:
        """
        Optimize portfolio using Modern Portfolio Theory
        
        Args:
            method: 'sharpe' for max Sharpe ratio, 'min_vol' for min volatility
        
        Returns:
            Dict with optimized weights and metrics
        """
        if self.returns_data is None:
            self.fetch_historical_data()
        
        n_assets = len(self.symbols)
        
        # Constraints: sum of weights = 1
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        
        # Bounds: weights between 0 and 1 (no short selling)
        bounds = Bounds(0, 1)
        
        # Initial weights (equal distribution)
        initial_weights = np.array([1/n_assets] * n_assets)
        
        if method == 'sharpe':
            # Maximize Sharpe Ratio
            def objective(weights):
                return -self._sharpe_ratio(weights)
        else:
            # Minimize volatility
            def objective(weights):
                return self._portfolio_volatility(weights)
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        optimized_weights = result.x
        
        return {
            'weights': optimized_weights,
            'symbols': self.symbols,
            'expected_return': self._portfolio_return(optimized_weights),
            'volatility': self._portfolio_volatility(optimized_weights),
            'sharpe_ratio': self._sharpe_ratio(optimized_weights),
            'method': method
        }
    
    def _portfolio_return(self, weights: np.ndarray) -> float:
        """Calculate expected portfolio return"""
        return np.dot(weights, self.mean_returns)
    
    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        """Calculate portfolio volatility"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def _sharpe_ratio(self, weights: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        return (self._portfolio_return(weights) - self.risk_free_rate) / self._portfolio_volatility(weights)
    
    def calculate_efficient_frontier(self, points: int = 50) -> Dict:
        """
        Calculate efficient frontier for visualization
        
        Returns:
            Dict with returns, volatility, and optimal portfolios
        """
        if self.returns_data is None:
            self.fetch_historical_data()
        
        n_assets = len(self.symbols)
        target_returns = np.linspace(
            self.mean_returns.min(),
            self.mean_returns.max() * 1.5,
            points
        )
        
        frontiers = []
        
        for target in target_returns:
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: self._portfolio_return(x) - target}
            ]
            bounds = Bounds(0, 1)
            initial = np.array([1/n_assets] * n_assets)
            
            result = minimize(
                lambda x: self._portfolio_volatility(x),
                initial,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                frontiers.append({
                    'return': target,
                    'volatility': self._portfolio_volatility(result.x),
                    'weights': result.x
                })
        
        # Add the max Sharpe portfolio
        sharpe_portfolio = self.optimize_portfolio('sharpe')
        
        # Add min volatility portfolio
        min_vol_portfolio = self.optimize_portfolio('min_vol')
        
        return {
            'frontier': frontiers,
            'max_sharpe': sharpe_portfolio,
            'min_volatility': min_vol_portfolio,
            'current_weights': self.current_weights,
            'symbols': self.symbols
        }
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate correlation matrix between assets"""
        if self.returns_data is None:
            self.fetch_historical_data()
        return self.returns_data.corr()
    
    def stress_test(self, scenario: str = 'mild_crash') -> Dict:
        """Historical stress test with scenario mapping.

        This runs a historical simulation using the stored `returns_data`:
        - computes portfolio daily returns from current weights
        - finds an analogous worst/bull window depending on scenario
        - returns drawdown metrics + a portfolio value path for visualization

        If historical simulation fails for any reason, falls back to the
        original fixed-impact approach.

        Scenarios:
        - 'mild_crash': analog window from mild drawdowns
        - 'severe_crash': analog window from severe drawdowns (like 2008)
        - 'recession': analog window from recession-like drawdowns
        - 'bull_run': analog window from best-performing periods
        - 'inflation': analog window from inflation-pressure drawdowns
        - 'rate_hike': analog window from rate-hike pressure drawdowns
        """

        scenarios = {
            'mild_crash': {'name': 'Mild Market Crash', 'description': 'Analog window from mild drawdowns', 'quantile': 0.20, 'window': 10, 'direction': 'down'},
            'severe_crash': {'name': 'Severe Market Crash', 'description': 'Analog window from severe drawdowns (like 2008)', 'quantile': 0.10, 'window': 30, 'direction': 'down'},
            'recession': {'name': 'Economic Recession', 'description': 'Analog window from recession-like drawdowns', 'quantile': 0.15, 'window': 20, 'direction': 'down'},
            'bull_run': {'name': 'Bull Market Run', 'description': 'Analog window from best-performing periods', 'quantile': 0.10, 'window': 20, 'direction': 'up'},
            'inflation': {'name': 'High Inflation', 'description': 'Analog window from inflation-pressure drawdowns', 'quantile': 0.18, 'window': 15, 'direction': 'down'},
            'rate_hike': {'name': 'Interest Rate Hike', 'description': 'Analog window from rate-hike pressure drawdowns', 'quantile': 0.20, 'window': 10, 'direction': 'down'},
        }

        scenario_data = scenarios.get(scenario, scenarios['mild_crash'])

        try:
            if self.returns_data is None:
                self.fetch_historical_data()

            if self.returns_data is None or self.returns_data.empty:
                raise ValueError("No historical returns data")

            weights = np.array(self.current_weights)

            # Compute portfolio daily return series from stored asset returns
            asset_matrix = self.returns_data.fillna(0.0).values
            portfolio_daily_returns = asset_matrix.dot(weights)
            portfolio_daily_returns = pd.Series(portfolio_daily_returns, index=self.returns_data.index)

            direction = scenario_data.get('direction', 'down')
            q = float(scenario_data['quantile'])
            w = int(scenario_data['window'])
            if w <= 1:
                w = 2

            # Identify candidate regime days by tail quantile
            if direction == 'up':
                candidate_mask = portfolio_daily_returns >= portfolio_daily_returns.quantile(1 - q)
            else:
                candidate_mask = portfolio_daily_returns <= portfolio_daily_returns.quantile(q)

            # Rolling cumulative return for window selection
            roll_cum = (1 + portfolio_daily_returns).rolling(window=w).apply(np.prod, raw=False) - 1
            roll_cum = roll_cum.dropna()

            if roll_cum.empty:
                raise ValueError("Unable to compute rolling stress returns")

            # Only consider windows whose end date lands on a candidate day
            candidate_end_idx = candidate_mask[candidate_mask].index.intersection(roll_cum.index)
            if len(candidate_end_idx) == 0:
                candidate_end_idx = roll_cum.index

            if direction == 'up':
                end_idx = roll_cum.loc[candidate_end_idx].idxmax()
            else:
                end_idx = roll_cum.loc[candidate_end_idx].idxmin()

            end_pos = portfolio_daily_returns.index.get_loc(end_idx)
            start_pos = max(0, end_pos - (w - 1))
            window_returns = portfolio_daily_returns.iloc[start_pos:end_pos + 1]

            start_value = float(self.total_value)

            # Build value path
            value_path = [start_value]
            current_value = start_value
            for r in window_returns.values:
                current_value = current_value * (1 + float(r))
                value_path.append(current_value)

            # Align dates with value_path (start + each day)
            dates = [window_returns.index[0]] + list(window_returns.index)
            value_series = pd.Series(value_path, index=pd.DatetimeIndex(dates))

            peak = float(value_series.max())
            trough = float(value_series.min())
            max_drawdown = ((trough - peak) / peak * 100.0) if peak > 0 else 0.0

            window_total_return_pct = (float(value_series.iloc[-1]) / start_value - 1) * 100.0
            worst_day_return_pct = float(window_returns.min()) * 100.0

            impacted_value = float(value_series.iloc[-1])
            loss = float(self.total_value - impacted_value)

            return {
                'scenario': scenario_data['name'],
                'description': scenario_data['description'],
                'impact_percent': window_total_return_pct,
                'current_value': float(self.total_value),
                'impacted_value': impacted_value,
                'loss': loss,
                'loss_percent': (loss / float(self.total_value)) * 100.0 if float(self.total_value) > 0 else 0.0,
                'max_drawdown_percent': float(max_drawdown),
                'worst_day_return_percent': float(worst_day_return_pct),
                'portfolio_path': [
                    {'date': str(d.date()), 'value': float(v)}
                    for d, v in value_series.items()
                ],
                'holdings': [
                    {
                        'symbol': h['symbol'],
                        'current_value': h['quantity'] * h['current_price'],
                        # Approximate stressed holding value proportionally to portfolio window move
                        'stressed_value': (h['quantity'] * h['current_price']) * (1 + (window_total_return_pct / 100.0)),
                        'loss': (h['quantity'] * h['current_price']) * (window_total_return_pct / 100.0)
                    }
                    for h in self.holdings
                ]
            }

        except Exception:
            # Fallback to original fixed-impact model
            fixed_scenarios = {
                'mild_crash': {'impact': -0.15, 'name': 'Mild Market Crash', 'description': '15% market correction'},
                'severe_crash': {'impact': -0.30, 'name': 'Severe Market Crash', 'description': '30% market crash (like 2008)'},
                'recession': {'impact': -0.20, 'name': 'Economic Recession', 'description': '20% decline during recession'},
                'bull_run': {'impact': 0.25, 'name': 'Bull Market Run', 'description': '25% market rally'},
                'inflation': {'impact': -0.10, 'name': 'High Inflation', 'description': '10% erosion due to inflation'},
                'rate_hike': {'impact': -0.08, 'name': 'Interest Rate Hike', 'description': '8% impact from rate hike'},
            }

            scenario_data = fixed_scenarios.get(scenario, fixed_scenarios['mild_crash'])
            current_value = float(self.total_value)
            impacted_value = current_value * (1 + scenario_data['impact'])
            loss = current_value - impacted_value

            return {
                'scenario': scenario_data['name'],
                'description': scenario_data['description'],
                'impact_percent': scenario_data['impact'] * 100,
                'current_value': current_value,
                'impacted_value': impacted_value,
                'loss': loss,
                'loss_percent': (loss / current_value) * 100 if current_value > 0 else 0,
                'max_drawdown_percent': None,
                'worst_day_return_percent': None,
                'portfolio_path': [],
                'holdings': [
                    {
                        'symbol': h['symbol'],
                        'current_value': h['quantity'] * h['current_price'],
                        'stressed_value': (h['quantity'] * h['current_price']) * (1 + scenario_data['impact']),
                        'loss': (h['quantity'] * h['current_price']) * scenario_data['impact']
                    }
                    for h in self.holdings
                ]
            }

    
    def get_rebalancing_suggestions(self, threshold: float = 0.05) -> Dict:
        """
        Get rebalancing suggestions based on current vs target weights
        
        Args:
            threshold: Deviation threshold to trigger rebalancing (default 5%)
        
        Returns:
            Dict with rebalancing suggestions
        """
        # Calculate target weights (using max Sharpe portfolio)
        target_portfolio = self.optimize_portfolio('sharpe')
        target_weights = target_portfolio['weights']
        
        # Current weights
        current_weights = np.array(self.current_weights)
        
        # Calculate deviations
        deviations = target_weights - current_weights
        
        suggestions = []
        for i, symbol in enumerate(self.symbols):
            if abs(deviations[i]) > threshold:
                action = 'BUY' if deviations[i] > 0 else 'SELL'
                amount = abs(deviations[i]) * self.total_value
                suggestions.append({
                    'symbol': symbol,
                    'action': action,
                    'current_weight': current_weights[i] * 100,
                    'target_weight': target_weights[i] * 100,
                    'deviation': deviations[i] * 100,
                    'amount': amount,
                    'priority': abs(deviations[i])
                })
        
        # Sort by priority (largest deviation first)
        suggestions.sort(key=lambda x: x['priority'], reverse=True)
        
        return {
            'needs_rebalancing': len(suggestions) > 0,
            'suggestions': suggestions,
            'current_weights': {s: w*100 for s, w in zip(self.symbols, current_weights)},
            'target_weights': {s: w*100 for s, w in zip(self.symbols, target_weights)}
        }
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        if self.returns_data is None:
            self.fetch_historical_data()
        
        # Calculate metrics
        current_return = self._portfolio_return(np.array(self.current_weights))
        current_volatility = self._portfolio_volatility(np.array(self.current_weights))
        current_sharpe = self._sharpe_ratio(np.array(self.current_weights))
        
        # Max Sharpe portfolio
        max_sharpe = self.optimize_portfolio('sharpe')
        
        # Min volatility portfolio
        min_vol = self.optimize_portfolio('min_vol')
        
        # Correlation matrix
        correlation = self.calculate_correlation_matrix()
        
        return {
            'current_portfolio': {
                'total_value': self.total_value,
                'return': current_return * 100,
                'volatility': current_volatility * 100,
                'sharpe_ratio': current_sharpe
            },
            'max_sharpe_portfolio': {
                'return': max_sharpe['expected_return'] * 100,
                'volatility': max_sharpe['volatility'] * 100,
                'sharpe_ratio': max_sharpe['sharpe_ratio'],
                'weights': {s: w*100 for s, w in zip(self.symbols, max_sharpe['weights'])}
            },
            'min_volatility_portfolio': {
                'return': min_vol['expected_return'] * 100,
                'volatility': min_vol['volatility'] * 100,
                'sharpe_ratio': min_vol['sharpe_ratio'],
                'weights': {s: w*100 for s, w in zip(self.symbols, min_vol['weights'])}
            },
            'correlation_matrix': correlation.to_dict(),
            'symbols': self.symbols
        }