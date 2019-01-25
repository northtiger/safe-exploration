# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 18:09:14 2017

@author: tkoller
"""
import warnings
import numpy as np
import datetime

from defaultconfig_episode import DefaultConfigEpisode
from os.path import basename, splitext,dirname
from os import makedirs, getcwd

from shutil import copy


class Config(DefaultConfigEpisode):
    """
    Options class for the exploration setting
    """


    
    # environment

    
    # safempc
    beta_safety=2.0
    n_safe = 4
    n_perf = 0
    r = 1
    
    #rl cost function
    cost = None
    ilqr_init = False



    def __init__(self):
        """ """
        #self.cost = super._generate_cost()
        super(Config,self).__init__(__file__)
	self.cost = super(Config,self)._generate_cost()
        
            
            
    
