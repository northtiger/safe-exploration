# -*- coding: utf-8 -*-
"""
Created on Wed Sep 20 11:13:29 2017

@author: tkoller
"""


from utils_ellipsoid import sum_ellipsoids,ellipsoid_from_box
from utils import compute_bounding_box_lagrangian, print_ellipsoid
from numpy import sqrt,trace,zeros,diag, eye
#from casadi import *

import numpy as np

def onestep_reachability(p_center,gp,K,k,L_mu,L_sigm,q_shape = None, c_safety = 1.,verbose = 1):
    """ Overapproximate the reachable set of states under affine control law
    
    given a system of the form:
        x_{t+1} = \mathcal{N}(\mu(x_t,u_t), \Sigma(x_t,u_t)),
    where x,\mu \in R^{n_s}, u \in R^{n_u} and \Sigma^{n_s \times n_s} are given bei the gp predictive mean and variance respectively
    we approximate the reachset of a set of inputs x_t \in \epsilon(p,Q)
    describing an ellipsoid with center p and shape matrix Q
    under the control low u_t = Kx_t + k 
    
    Parameters
    ----------
        p_center: n_s x 1 array[float]     
            Center of state ellipsoid        
        gp: SimpleGPModel     
            The gp representing the dynamics            
        K: n_u x n_s array[float]     
            The state feedback-matrix for the controls         
        k: n_u x 1 array[float]     
            The additive term of the controls
        L_mu: 1d_array of size n_s
            Set of Lipschitz constants on the Gradients of the mean function (per state dimension)
        L_sigm: 1d_array of size n_s
            Set of Lipschitz constants of the predictive variance (per state dimension)
        q_shape: np.ndarray[float], array of shape n_s x n_s, optional
            Shape matrix of state ellipsoid
        c_safety: float, optional
            The scaling of the semi-axes of the uncertainty matrix 
            corresponding to a level-set of the gaussian pdf.        
        verbose: int
            Verbosity level of the print output            
    Returns:
    -------
        p_new: n_s x 1 array[float]
            Center of the overapproximated next state ellipsoid
        Q_new: np.ndarray[float], array of shape n_s x n_s
            Shape matrix of the overapproximated next state ellipsoid  
    """
   
    if verbose > 0:
        if not q_shape is None:
            print_ellipsoid(p_center,q_shape,text="initial uncertainty ellipsoid")
        
    n_u, n_s = np.shape(K)
    
    if q_shape is None: # the state is a point
        u_p = np.dot(K,p_center) + k
        
        if verbose >0:
            print("\nApplying action:")
            print(u_p)
            
        z_bar = np.vstack((p_center,u_p))
        p_new, q_new_unscaled = gp.predict(z_bar.T)
        q_1 = np.diag(q_new_unscaled.squeeze() * c_safety)
        
        p_1 = p_center + p_new.T
        
        if verbose >0:
            print_ellipsoid(p_1,q_1,text="uncertainty first state")
        
        return p_1, q_1
    else: # the state is a (ellipsoid) set
        ## compute the linearization centers
        x_bar = p_center   # center of the state ellipsoid
        u_bar = k   # u_bar = K*(u_bar-u_bar) + k = k
        z_bar = np.vstack((x_bar,u_bar))
        
        if verbose >0:
            print("\nApplying action:")
            print(u_bar)
        ##compute the zero and first order matrices
        mu_0, sigm_0 = gp.predict(z_bar.T)
        
        if verbose > 0:
            print_ellipsoid(mu_0,diag(sigm_0.squeeze()),text="predictive distribution")
            
        Jac_mu = gp.predictive_gradients(z_bar.T)
        A_mu = Jac_mu[0,:,:n_s]
        B_mu = Jac_mu[0,:,n_s:]
         
        ## reach set of the affine terms
        H = A_mu + np.dot(B_mu,K)
        p_0 = mu_0.T + np.dot(B_mu,k-u_bar)
        
        Q_0 = np.dot(H,np.dot(q_shape,H.T))
        
        if verbose > 0:
            print_ellipsoid(p_0,Q_0,text="linear transformation uncertainty")
        ## computing the box approximate to the lagrange remainder
        lb_mean,ub_mean = compute_bounding_box_lagrangian(p_center,q_shape,L_mu,K,k,order = 2,verbose = verbose)
        lb_sigm,ub_sigm = compute_bounding_box_lagrangian(p_center,q_shape,L_sigm,K,k,order = 1,verbose = verbose)
        
        Q_lagrange_sigm = diag(c_safety*(ub_sigm+sqrt(sigm_0[0,:]))**2)   
        p_lagrange_sigm = zeros((n_s,1))
        
        if verbose > 0:
            print_ellipsoid(p_lagrange_sigm,Q_lagrange_sigm,text="overapproximation lagrangian sigma")
    

        Q_lagrange_mu = ellipsoid_from_box(lb_mean,ub_mean,diag_only = True)
        p_lagrange_mu = zeros((n_s,1))
        
        if verbose > 0:
            print_ellipsoid(p_lagrange_mu,Q_lagrange_mu,text="overapproximation lagrangian mu")
        
        p_sum_lagrange,Q_sum_lagrange = sum_ellipsoids(p_lagrange_sigm,Q_lagrange_sigm,p_lagrange_mu,Q_lagrange_mu)
        
        p_new , Q_new = sum_ellipsoids(p_sum_lagrange,Q_sum_lagrange,p_0,Q_0) 
        
        print_ellipsoid(p_new,Q_new,text="accumulated uncertainty current step")
        p_1, q_1 = sum_ellipsoids(p_new,Q_new,p_center,q_shape)
        print_ellipsoid(p_1,q_1,text="sum old and new uncertainty")
        
        return p_1,q_1
        
        
def multistep_reachability(p_0,gp,K,k,L_mu,L_sigm,q_0 = None, c_safety = 1.,verbose = 1):
    """ Ellipsoidal overapproximation of a probabilistic safe set after multiple actions
    
    Overapproximate the region containing a pre-specified percentage of the probability
    mass of the system after n actions are applied to the system. The overapproximating
    set is given by an ellipsoid.
    
    Parameters
    ----------
    
    p_0: n_s x 1 array[float]     
            Center of state ellipsoid        
    gp: SimpleGPModel     
        The gp representing the dynamics            
    K: n x n_u x n_s array[float]     
        The state feedback-matrices for the controls at each time step        
    k: n x n_u array[float]     
        The additive term of the controls at each time step
    L_mu: 1d_array of size n_s
        Set of Lipschitz constants on the Gradients of the mean function (per state dimension)
    L_sigm: 1d_array of size n_s
        Set of Lipschitz constants of the predictive variance (per state dimension)
    q_shape: np.ndarray[float], array of shape n_s x n_s, optional
        Shape matrix of the initial state ellipsoid
    c_safety: float, optional
        The scaling of the semi-axes of the uncertainty matrix 
        corresponding to a level-set of the gaussian pdf.        
    verbose: int
        Verbosity level of the print output            
    
    """
    n, n_u, n_s = np.shape(K)
    
    K_0 = K[0]
    k_0 = k[0,:,None]
    p_1,q_1 = onestep_reachability(p_0,gp,K_0,k_0,L_mu,L_sigm,q_shape=None,c_safety=c_safety,verbose = verbose)
    
    raise NotImplementedError("Still need to work on this!")