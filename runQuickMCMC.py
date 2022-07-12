"""C 2021 Bence Becsy
MCMC for CW fast likelihood (w/ Neil Cornish and Matthew Digman)"""

import numpy as np
np.seterr(all='raise')
import matplotlib.pyplot as plt
#import corner

import pickle

import enterprise
from enterprise.pulsar import Pulsar
import enterprise.signals.parameter as parameter
from enterprise.signals import utils
from enterprise.signals import signal_base
from enterprise.signals import selections
from enterprise.signals.selections import Selection
from enterprise.signals import white_signals
from enterprise.signals import gp_signals
from enterprise.signals import deterministic_signals
import enterprise.constants as const

from enterprise_extensions import deterministic

#import glob
#import json

import QuickCW
from QuickMCMCUtils import ChainParams,EvolveParams
#import CWFastLikelihoodNumba

#make sure this points to the pickled pulsars you want to analyze
data_pkl = 'data/nanograv_11yr_psrs.pkl'

with open(data_pkl, 'rb') as psr_pkl:
    psrs = pickle.load(psr_pkl)

print(len(psrs))

#number of iterations (increase to 100 million - 1 billion for actual analysis)
N = 5000000

n_int_block = 10_000 #number of iterations in a block (which has one shape update and the rest are projection updates)
save_every_n = 100_000 #number of iterations between saving intermediate results (needs to be intiger multiple of n_int_block)
N_blocks = np.int64(N//n_int_block) #number of blocks to do
fisher_eig_downsample = 2000 #multiplier for how much less to do more expensive updates to fisher eigendirections for red noise and common parameters compared to diagonal elements

n_status_update = 100 #number of status update printouts (N/n_status_update needs to be an intiger multiple of n_int_block)
n_block_status_update = np.int64(N_blocks//n_status_update) #number of bllocks between status updates

assert N_blocks%n_status_update ==0 #or we won't print status updates
assert N%save_every_n == 0 #or we won't save a complete block
assert N%n_int_block == 0 #or we won't execute the right number of blocks

#Parallel tempering prameters
T_max = 3.
n_chain = 4

#make sure this points to your white noise dictionary
noisefile = 'data/quickCW_noisedict_kernel_ecorr.json'

#this is where results will be saved
savefile = 'results/quickCW_test16.h5'
#savefile = None

#Setup and start MCMC
#object containing common parameters for the mcmc chain which cannot change for the lifetime of the chain object
chain_params = ChainParams(T_max,n_chain,
                           n_int_block=n_int_block, #number of iterations in a block (which has one shape update and the rest are projection updates)
                           save_every_n=save_every_n, #number of iterations between saving intermediate results (needs to be intiger multiple of n_int_block)
                           fisher_eig_downsample=fisher_eig_downsample) #multiplier for how much less to do more expensive updates to fisher eigendirections for red noise and common parameters compared to diagonal elements
#separate object for parameters which are allowed to change between calls to advance_N_blocks
evolve_params = EvolveParams(n_block_status_update,\
                     savefile = savefile,#hdf5 file to save to, will not save at all if None
                     thin=100)  #thinning, i.e. save every `thin`th sample to file (increase to higher than one to keep file sizes small)

pta,mcc = QuickCW.QuickCW(chain_params, psrs, noise_json=noisefile)

#Do the main MCMC iteration
mcc.advance_N_blocks(evolve_params,N_blocks)
