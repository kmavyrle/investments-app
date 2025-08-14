import pandas as pd
import numpy as np  
from scipy.stats import norm
import math


class Option:
    def __init__(self, S, K, r, T,sigma,cp = 'c',q = 0):
        self.S = S  # Current stock price
        self.K = K  # Strike price
        self.r = r  # Risk-free interest rate
        self.T = T  # Time to expiration in years
        self.sigma = sigma  # Volatility of the underlying asset
        self.q = q  # Dividend yield (default is 0)
        self.cp = cp  # 'c' for call option, 'p' for put option

    def d1(self):
        return (math.log(self.S / self.K) + (self.r - self.q + 0.5 * self.sigma ** 2) * self.T) / (self.sigma * math.sqrt(self.T))

    def d2(self):
        return self.d1() - self.sigma * math.sqrt(self.T)

    def bsprice(self):
        """
        Calculate the Black-Scholes price of a European call option.

        Parameters:
        S: Stock Price
        K: Strike Price
        r: Risk-free interest rate (annualized)
        T: Time to expiration (in years)
        sigma: Implied volatility of the underlying asset (annualized)
        cp: Call or Put option ('c' for call, 'p' for put)
        """
        S = self.S
        K = self.K 
        q = self.q
        r = self.r 
        T = self.T

        d1 = self.d1()
        d2 = self.d2()
        cp = self.cp
        if cp == 'c':
            price = (S * np.exp(-q * T) * norm.cdf(d1)) - (K * np.exp(-r * T) * norm.cdf(d2))
        elif cp == 'p':
            price = (K * np.exp(-r * T) * norm.cdf(-d2)) - (S * np.exp(-q * T) * norm.cdf(-d1))
        
        return price
    
    def get_payoff(self,St):
        """
        Calculate the payoff of a European option at expiration.

        Parameters:
        S: Stock Price at expiration
        K: Strike Price
        cp: Call or Put option ('c' for call, 'p' for put)
        """
        cp = self.cp
        if cp == 'c':
            return max(0, St - self.K)
        elif cp == 'p':
            return max(0, self.K - St)
        
    def get_payoffs(self,St_range):
        """
        Calculate the payoffs of a European option over a range of stock prices at expiration.

        Parameters:
        St_range: Range of stock prices at expiration
        K: Strike Price
        cp: Call or Put option ('c' for call, 'p' for put)
        """
        payoffs = [self.get_payoff(St) for St in St_range]
        payoffs = pd.DataFrame(payoffs, columns=['Payoff'])
        payoffs.index = St_range
        payoffs.index.name = 'St'
        return payoffs
    