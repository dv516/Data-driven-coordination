# -*- coding: utf-8 -*-
"""
Created on Fri Jul  2 22:33:43 2021

@author: dv516
"""

# import DDC
from src.Problems.ToyProblem1 import f1, f2

from src.Algorithms.PyBobyqa_wrapped.Wrapper_for_pybobyqa import PyBobyqaWrapper
from src.Algorithms.DIRECT_wrapped.Wrapper_for_Direct import DIRECTWrapper
from src.Algorithms.ALADIN_Data import System as ALADIN_Data
from src.Algorithms.ADMM_Scaled_Consensus import System as ADMM_Scaled
# from Algorithms.Coordinator_Augmented import System as Coordinator_ADMM
from src.Algorithms.Coordinator_explConstr import System as Coordinator_withConstr
from src.Algorithms.CUATRO import CUATRO
from GPyOpt.methods import BayesianOptimization

import numpy as np
import matplotlib.pyplot as plt
import pyomo.environ as pyo
import pickle

from src.utilities import postprocessing, postprocessing_List, preprocess_BO, postprocess_ADMM


N_it = 50

N = 2
N_var = 3
N_runs = 5
list_fi = [f1, f2]

global_ind = [3]
dim = len(global_ind)
index_agents = {1: [1, 3], 2: [2, 3]}
z = {3: 4.5}

actual_f = 13.864179350870021
actual_x = 0.398

save_data_list = []

rho = 5000 # just done 500, now do 5000

ADMM_Scaled_system = ADMM_Scaled(N, N_var, index_agents, global_ind)
ADMM_Scaled_system.initialize_ADMM(rho/10, N_it, list_fi, z)
ADMM_Scaled_system.solve_ADMM()
objct = postprocess_ADMM(ADMM_Scaled_system)
save_data_list += [postprocess_ADMM(ADMM_Scaled_system)]


s = 'ADMM_Scaled'
print(s+': ', 'Done')

# rho = 5000 # previous run was 500 # originally 5000

x0 = np.array([z[3]])
bounds = np.array([[-10, 10]])
init_trust = 1
beta = 0.5


CUATRO1_List = []
s = 'Coordinator'
for i in range(1):
    Coordinator_withConstr_system = Coordinator_withConstr(N, N_var, index_agents, global_ind)
    Coordinator_withConstr_system.initialize_Decomp(rho, N_it, list_fi, z)
    output_Coord = Coordinator_withConstr_system.solve(CUATRO, x0, bounds, init_trust, 
                            budget = N_it, beta_red = beta, rnd_seed=i)    
    CUATRO1_List += [output_Coord]
    print(s + ' run ' + str(i+1) + ': Done')
    
save_data_list += [CUATRO1_List]


A_dict = {1: np.array([[1]]), 2: np.array([[-1]])}
s = 'ALADIN_Data'
CUATRO2_List = []
for i in range(1):
    System_dataAL = ALADIN_Data(N, N_var, index_agents, global_ind)
    System_dataAL.initialize(rho, N_it, z, list_fi, A_dict, seed=i)
    System_dataAL.solve(6, init_trust, mu = 1e7)
    CUATRO2_List += [System_dataAL]
    print(s + ' run ' + str(i+1) + ': Done')

save_data_list += [CUATRO2_List]

def f_pbqa(x):
    z_list = {global_ind[i]: [x[i]] for i in range(dim)}
    return np.sum([pyo.value(list_fi[i](z_list, rho, global_ind, index_agents[i+1]).obj) for i in range(N)]), [0]
f_DIR = lambda x, grad: f_pbqa(x)
def f_BO(x):
    if x.ndim > 1:
       x_temp = x[-1] 
    else:
       x_temp = x
    # temp_dict = {i+1: x[:,i] for i in range(len(x))}
    z_list = {global_ind[i]: [x_temp[i]] for i in range(dim)}
    return np.sum([pyo.value(list_fi[i](z_list, rho, global_ind, index_agents[i+1]).obj) for i in range(N)])


pybobyqa = PyBobyqaWrapper().solve(f_pbqa, x0, bounds=bounds.T, \
                                      maxfun=N_it, constraints=1, \
                                      seek_global_minimum= True, \
                                      objfun_has_noise=False)
    
save_data_list += [pybobyqa]

domain = [{'name': 'var_'+str(i+1), 'type': 'continuous', 'domain': (-10,10)} for i in range(dim)]
y0 = np.array([f_BO(x0)])



s = 'DIRECT'
DIRECT_List = []
for i in range(N_runs): 
    DIRECT =  DIRECTWrapper().solve(f_DIR, x0, bounds, maxfun = N_it, 
                                   constraints=1)
    DIRECT['f_best_so_far'][0] = float(y0)
    DIRECT_List += [DIRECT]
    print(s + ' run ' + str(i+1) + ': Done')

save_data_list += [DIRECT_List]

s = 'BO'
BO_List = []
for i in range(N_runs):
    BO = BayesianOptimization(f=f_BO, domain=domain, X=x0.reshape((1,dim)), Y=y0.reshape((1,1)))
    BO.run_optimization(max_iter=N_it)
    BO_post = preprocess_BO(BO.Y.flatten(), y0)
    BO_List += [BO_post]
    print(s + ' run ' + str(i+1) + ': Done')

save_data_list += [BO_List]

s_list = ['ADMM', 'ADMM_CUATRO', 'ALADIN_CUATRO', 'Py-BOBYQA', 
          'DIRECT-L', 'GPyOpt']

dim = len(x0)
problem = 'MotivatingExample_'


for k in range(len(s_list)):
    with open('../Data/'+ problem + str(N) + 'ag_' + str(dim) +'dim_'+ s_list[k] + '.pickle', 'wb') as handle:
        pickle.dump(save_data_list[k], handle, protocol=pickle.HIGHEST_PROTOCOL) 


data_dict = {}
for k in range(len(s_list)):
    with open('../Data/'+ problem + str(N) + 'ag_' + str(dim) +'dim_'+ s_list[k] + '.pickle', 'rb') as handle:
        data_dict[s_list[k]] = pickle.load(handle)


fig1 = plt.figure() 
ax1 = fig1.add_subplot() 
fig2 = plt.figure() 
ax2 = fig2.add_subplot() 

s = 'ADMM'
out = postprocessing(ax1, ax2,  s, data_dict[s], actual_f, c='dodgerblue')
ax1, ax2 = out

s = 'ADMM_CUATRO'
out = postprocessing_List(ax1, ax2, s, data_dict[s], actual_f, coord_input = True, c='darkorange', N_it=N_it)
ax1, ax2 = out

s = 'Py-BOBYQA'
out = postprocessing(ax1, ax2, s, data_dict[s], actual_f, coord_input = True, c='green')
ax1, ax2 = out

s = 'DIRECT-L'
out = postprocessing_List(ax1, ax2, s, data_dict[s], actual_f, coord_input = True, c='red', N_it=N_it)
ax1, ax2 = out

s = 'ALADIN_CUATRO'
out = postprocessing_List(ax1, ax2, s, data_dict[s], actual_f, ALADIN = True, c='darkviolet', N_it=N_it, N=N)
ax1, ax2 = out

s = 'GPyOpt'
out = postprocessing_List(ax1, ax2, s, data_dict[s], actual_f, BO = True, c='saddlebrown', N_it=N_it)
ax1, ax2 = out


# ax1.scatter
# ax2.plot(np.array([1, 51]), np.array([actual_f, actual_f]), c = 'red', label = 'optimum')
ax1.set_xlabel('Number of function evaluations')
ax1.set_ylabel('Convergence')
ax1.set_yscale('log')
ax1.legend()

# ax1.scatter
# ax2.plot(np.array([1, 51]), np.array([actual_f, actual_f]), c = 'red', label = 'optimum')
ax2.set_xlabel('Number of function evaluations')
ax2.set_ylabel('Best function evaluation')
ax2.set_yscale('log')
ax2.plot([1, N_it], [actual_f, actual_f], '--k', label = 'Centralized')
ax2.legend()

problem = 'Test_function_1'
fig1.savefig('../Figures/' + problem +'_conv.svg', format = "svg")
fig2.savefig('../Figures/' + problem +'_evals.svg', format = "svg")


# def post_2d(ax, string, result, actual_f, s = 10, c = 'k', init=None,
#                     coord_input = False, ALADIN = False, samecoord = False, BO = False):
#     if BO:
#         obj_global = result.get_evaluations()[1].flatten()
#         z_arr = result.get_evaluations()[0].flatten()
#         N_len = min(len(obj_global), len(z_arr))
#         ax.scatter(z_arr[:N_len], obj_global[:N_len], label=string, s=10)
#     elif ALADIN:
#         if samecoord:
#             obj_arr = np.array(result.best_obj)
#             z_arr = np.array(result.center_list)
#             ax.scatter(z_arr, obj_arr, label=string, s=10)
#         else:
#             obj_global = np.sum(np.array([result.obj[i+1] for i in range(N)]), axis = 0)
#             z_arr = np.mean([result.z_list[idx+1][global_ind[0]] for idx in range(N)], axis = 0)
#             ax.scatter(z_arr, obj_global, label=string, s=10)
#     elif not coord_input:
#         obj_arr = np.sum(np.array([result.obj[i+1] for i in range(N)]), axis = 0)
#         z_arr = np.array(result.z_list[global_ind[0]])
#         if not samecoord:
#             ax.scatter(z_arr[1:], obj_arr, label=string, s=10)
#         else:
#             ax.scatter(z_arr, obj_arr, label=string, s=10)  
#     else:
#         f = np.array(result['f_store'])
#         x_list = np.array([result['x_store']]).flatten()
#         N_len = min(len(f), len(x_list))
#         ax.scatter(x_list[:N_len], f[:N_len], label=string, s=10)
        
#     return ax


# fig = plt.figure() 
# ax = fig.add_subplot() 

# s = 'ADMM_Scaled'
# out = post_2d(ax,  s, ADMM_Scaled_system, actual_f)
# ax=out

# s = 'CUATRO_1'
# out = post_2d(ax, s, output_Coord, actual_f, coord_input = True)
# ax=out

# s = 'CUATRO_2'
# out = post_2d(ax, s, System_dataAL, actual_f, ALADIN = True, init=float(y0))
# ax=out

# ax.scatter(actual_x, actual_f, c = 'black', label = 'Optimum')
# ax.scatter(z[3], float(y0),  s = 25, marker = 'X', c = 'black', label = 'Starting point')
# ax.set_xlabel('Shared variable $x_3$')
# ax.set_ylabel('Function evaluation')
# ax.legend(loc = 'lower right')
# ax.set_yscale('log')
# ax.set_xlim([-2, 6])
# ax.set_ylim([10, 100])

# # fig.savefig('../Figures/' + problem +'_1d_1.svg', format = "svg")


# fig = plt.figure() 
# ax = fig.add_subplot() 

# s = 'Py-BOBYQA'
# out = post_2d(ax, s, pybobyqa, actual_f, coord_input = True)
# ax=out

# s = 'DIRECT-L'
# out = post_2d(ax, s, DIRECT, actual_f, coord_input = True)
# ax=out

# s = 'BO'
# out = post_2d(ax, s, BO, actual_f, BO = True)
# ax=out

# ax.scatter(actual_x, actual_f, c = 'black', label = 'Optimum')
# ax.scatter(z[3], float(y0),  s = 25, marker = 'X', c = 'black', label = 'Starting point')
# ax.set_xlabel('Shared variable $x_3$')
# ax.set_ylabel('Function evaluation')
# ax.legend(loc = 'lower right')
# ax.set_yscale('log')
# ax.set_xlim([-2, 6])
# ax.set_ylim([10, 100])

# # fig.savefig('../Figures/' + problem +'_1d_2.svg', format = "svg")


# # # fig = plt.figure() 
# # # ax = fig.add_subplot() 

# # # z_linspace = np.linspace(-2, 6, 100).reshape((100, 1))
# # # obj = np.array([f_pbqa(x) for x in z_linspace])

# # # ax.plot(z_linspace.flatten(), obj[:,0])
# # # ax.set_xlabel('Shared variable $x_3$')
# # # ax.set_ylabel('Function evaluation')
# # # ax.legend(loc = 'lower right')
# # # ax.set_yscale('log')
# # # ax.set_xlim([-2, 6])
# # # ax.set_ylim([10, 100])

# # # fig.savefig('../Figures/' + problem +'_1d_true.svg', format = "svg")

