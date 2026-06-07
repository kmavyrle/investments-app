import numpy as np
import pandas as pd
import cvxpy as cp
import statsmodels.api as sm
from sklearn.covariance import LedoitWolf



class pyOpt:
    def __init__(self,raw_rets = None):
        self.raw_rets = raw_rets
        self.mu = raw_rets.mean()
        self.Sigma = raw_rets.cov()
        self.Sigma =LedoitWolf().fit(raw_rets).covariance_

    def get_cov_mat(self):
        #Function returns the returns covar matrix input
        return self.Sigma
    
    def get_expected_returns(self):
        return self.mu
    
    def get_mkt_beta_brkdown(self, benchmk_col):
        """
        Returns Series of full-sample CAPM betas vs benchmark
        """
        X = self.raw_rets[benchmk_col]

        betas = {}

        for col in self.raw_rets.columns:
            if col == benchmk_col:
                continue

            Y = self.raw_rets[col]

            df = pd.concat([Y, X], axis=1).dropna()
            df.columns = ["y", "x"]

            X_reg = sm.add_constant(df["x"])
            beta = sm.OLS(df["y"], X_reg).fit().params["x"]

            betas[col] = beta

        return pd.Series(betas)
    
    def get_downside_beta_brkdown(self, benchmk_col):
        """
        Returns Series of downside CAPM betas vs benchmark
        (only days when benchmark return < 0)
        """
        X = self.raw_rets[benchmk_col]

        betas = {}

        for col in self.raw_rets.columns:
            if col == benchmk_col:
                continue

            Y = self.raw_rets[col]

            df = pd.concat([Y, X], axis=1).dropna()
            df.columns = ["y", "x"]

            # keep only market down days
            df = df[df["x"] < 0]

            if len(df) < 10:   # avoid garbage estimates
                betas[col] = float("nan")
                continue

            X_reg = sm.add_constant(df["x"])
            beta = sm.OLS(df["y"], X_reg).fit().params["x"]

            betas[col] = beta

        return pd.Series(betas)
    
    def get_upside_beta_brkdown(self, benchmk_col):
        """
        Returns Series of downside CAPM betas vs benchmark
        (only days when benchmark return < 0)
        """
        X = self.raw_rets[benchmk_col]

        betas = {}

        for col in self.raw_rets.columns:
            if col == benchmk_col:
                continue

            Y = self.raw_rets[col]

            df = pd.concat([Y, X], axis=1).dropna()
            df.columns = ["y", "x"]

            # keep only market down days
            df = df[df["x"] > 0]

            if len(df) < 10:   # avoid garbage estimates
                betas[col] = float("nan")
                continue

            X_reg = sm.add_constant(df["x"])
            beta = sm.OLS(df["y"], X_reg).fit().params["x"]

            betas[col] = beta

        return pd.Series(betas)
    
    def get_constraint_vector(self,w,kappa,mu= None,Sigma=None,min_rets=None,max_vol=None,min_w=None,max_w=None,beta = None):
        '''
        w: cp variable as input
        mu: array of expected returns
        Sigma: covariance matrix of returns
        kappa: cp variable for risk aversion
        min_rets: minimum returns constraint for the total portfolio
        max_vol: maximum standard deviation constraint for the total portfolio
        min_w: minimum weight constraint for each asset
        max_w: maximum weight constraint for each asset
        '''
        if mu is None:
            mu = self.mu
        if Sigma is None:
            Sigma = self.Sigma
        #Sigma.fillna(0,inplace = True)
        constraints = [w @ mu ==1,
                       cp.sum(w)==kappa,]
                    #kappa >=0]
    
        # Add beta-neutral constraint if beta vector is provided
        if beta is not None:
            constraints.append(w @ beta == 0)        
        for c in [min_rets,max_vol,min_w,max_w]:
            if c is not None:
                if c == min_rets:
                    constraints.append(w.T @ mu >= min_rets)
                elif c == max_vol:
                    constraints.append(cp.quad_form(w, Sigma) <= max_vol**2)
                elif c == min_w:
                    constraints.append(w >= min_w)
                elif c == max_w:
                    constraints.append(w <= max_w)
        return constraints
    
    def get_max_sharpe_wts(self,mu = None,Sigma = None,total_port_wt = 1,min_rets=None,
                           max_vol=None,min_w=None,max_w=None,beta = None):
            '''
            Function gets maximum sharpe ratio portfolio weights
            mu: array of expected returns
            Sigma: covariance matrix of returns
            total_port_wt: total portfolio weight (default is 1)
            min_rets: minimum returns constraint for the total portfolio
            max_vol: maximum volatility constraint for the total portfolio
            min_w: minimum weight constraint for each asset
            max_w: maximum weight constraint for each asset

            Returns: Maximum sharpe ratio portfolio weights
            '''
            if mu is None:
                mu = self.mu
            if Sigma is None:
                Sigma = self.Sigma
                
            mu = np.array(mu) # convert to numpy array if not already
            n = len(mu)
            # Sharpe ratio Reformulation
            w = cp.Variable(n)
            portfolio_vol = cp.quad_form(w, Sigma)
            objective = portfolio_vol
            kappa = cp.Variable()

            # Constraints
            constraints = self.get_constraint_vector(w,kappa,mu,Sigma,min_rets,max_vol,min_w,max_w,beta)

            # Formulate problem
            problem = cp.Problem(cp.Minimize(objective), constraints)
            problem.solve()
            print("status:", problem.status)
            print("objective:", problem.value)
            print("kappa:", kappa.value)
            print("w:", w.value)
            #print(w.value)
            if total_port_wt ==1:
                w = w.value/np.sum(w.value)
            elif total_port_wt ==0:
                #print(kappa.value)
                w = w.value - np.mean(w.value)#/(sum(abs(w.value)))-1/len(w.value) + total_port_wt
                w = w/(sum(abs(w)))
            else:
                w = w.value
                w = w/(sum(abs(w)))
                
            return w


    def get_max_sortino_wts(self, mu=None, total_port_wt=1, min_rets=None, max_vol=None, 
                            min_w=None, max_w=None, beta=None):
        '''
        Function gets maximum Sortino ratio portfolio weights
        Sortino ratio uses downside deviation (returns <= 0) instead of total volatility
        
        Parameters:
        -----------
        mu: array of expected returns
        total_port_wt: total portfolio weight (default is 1)
        min_rets: minimum returns constraint for the total portfolio
        max_vol: maximum volatility constraint for the total portfolio
        min_w: minimum weight constraint for each asset
        max_w: maximum weight constraint for each asset
        beta: array of betas for beta-neutral constraint
        
        Returns: Maximum Sortino ratio portfolio weights
        '''
        if mu is None:
            mu = self.mu
        
        mu = np.array(mu)
        rets = self.raw_rets  # Use historical returns from class
        n = len(mu)
        
        # Compute downside covariance matrix (only negative returns)
        downside_rets = rets.copy()
        downside_rets[downside_rets > 0] = 0  # Zero out positive returns
        
        # Downside covariance (semi-covariance)
        downside_cov = np.cov(downside_rets.T)
        
        # Make sure it's positive semi-definite
        min_eig = np.min(np.linalg.eigvals(downside_cov))
        if min_eig < 0:
            downside_cov += (-min_eig + 1e-8) * np.eye(n)
        
        # Sortino ratio Reformulation
        w = cp.Variable(n)
        portfolio_downside_risk = cp.quad_form(w, downside_cov)
        objective = portfolio_downside_risk
        kappa = cp.Variable()
        
        # Constraints
        constraints = self.get_constraint_vector(w, kappa, mu, downside_cov, 
                                                min_rets, max_vol, min_w, max_w, beta)
        
        # Formulate problem
        problem = cp.Problem(cp.Minimize(objective), constraints)
        problem.solve()
        
        print("status:", problem.status)
        print("objective:", problem.value)
        print("kappa:", kappa.value)
        print("w:", w.value)
        
        # Check if solution exists
        if w.value is None or kappa.value is None:
            print("Optimization failed!")
            return None
        
        # Rescale weights based on total_port_wt
        if total_port_wt == 1:
            w = w.value / np.sum(w.value)
        elif total_port_wt == 0:
            w = w.value - np.mean(w.value)
            w = w / sum(abs(w))
        else:
            w = w.value
            w = w / sum(abs(w))
        
        return w