import cvxpy as cvx
import numpy as np

def create_fused_lasso(W, g):
    reg = 0
    inds = W.nonzero()
    rows = np.asarray(inds[0]).T.squeeze()
    cols = np.asarray(inds[1]).T.squeeze()
    if rows.size == 0 or len(rows.shape) == 0:
        return reg
    for i in range(rows.shape[0]):
        row = rows[i]
        col = cols[i]
        if row == col:
            continue
        Wij = W[row,col]
        '''
        if i >= j or Lij == 0:
            continue
        '''
        reg = reg +  Wij*cvx.abs(g[row]-g[col])
    return reg
