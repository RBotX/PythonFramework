import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
from scipy.special import expit as sigmoid

def plot_function(xrange, f, axis_obj, n_samples=1000.0):
    x = np.arange(xrange[0], xrange[1], (xrange[1] - xrange[0])/n_samples)
    #y = np.asarray([f(xi) for xi in x])
    y = f(x)
    axis_obj.plot(x, y)
    axis_obj.set_xlabel('f(x)')
    axis_obj.set_ylabel('p(f(x))')

def plot_function_2d(xrange, yrange, f, axis_obj, n_samples=1000.0):
    x = np.arange(xrange[0], xrange[1], (xrange[1] - xrange[0])/n_samples)
    y = np.arange(yrange[0], yrange[1], (yrange[1] - yrange[0])/n_samples)
    X, Y = np.meshgrid(x, y)
    #xy = zip(X,Y)
    #z = [f(xyi) for xyi in xy]
    Z = f((X,Y))
    axis_obj.contourf(X, Y, Z, cmap=cm.gray)
    print 'min: ' + str(Z.min())
    print 'max: ' + str(Z.max())
    axis_obj.set_xlabel('f(x)')
    axis_obj.set_ylabel('f(y)')

def plot_pairwise(a):
    f = lambda x: sigmoid(4-x)
    plot_function([-8,8], f, a)
    a.set_title('Pairwise')

def plot_pairwise_contour(a):
    f = lambda xy: sigmoid(xy[0]-xy[1])
    plot_function_2d([-8,8], [-8, 8], f, a)
    a.set_title('Relative')

def plot_bound(a):
    c1 = 2
    c2 = 4
    f = lambda x: sigmoid(c2-x) - sigmoid(c1 - x)
    plot_function([-0,6], f, a)
    a.set_title('Bound')

def plot_similar(a):
    s = 1
    f = lambda x: sigmoid(s-x) + sigmoid(-s-x)
    plot_function([-7.5, 7.5], f, a)
    a.set_title('Similar')

def plot_similar_contour(a):
    s = 1
    f = lambda x: sigmoid(s-(x[0] - x[1])) - sigmoid(-s-(x[0] - x[1]))
    plot_function_2d([-7.5, 7.5], [-7.5, 7.5], f, a)
    a.set_title('Similar')

def plot_neighbor(a):
    yi = 1
    yj = 0
    yk = 1
    h = lambda x: 1 - np.exp(-x)
    f = lambda x: min(h(yk-yj), h(yk-yi))
    plot_function([-1,(yk-yj)/2], f, a)
    a.set_title('Neighbor')

def plot_neighbor_contour(a):
    yk = 4
    hx = lambda x: 1 - np.exp(-x)
    #f = lambda x: np.minimum(hx(yk-x[0]), hx(yk-x[1]))
    f = lambda x: np.minimum(hx(yk-x[1]), hx(yk+x[1] - 2*x[0]))
    #f = lambda x: sigmoid(yk-x[0]) - sigmoid(-x[1]-yk+2*x[0])
    plot_function_2d([-4,4], [-4,4], f, a)
    a.set_title('Neighbor')

def plot_hyp_pos(a):
    f = lambda x: (x[0] + x[1])**2 / (x[0]**2 + x[1]**2)
    plot_function_2d([-4, 4], [-4, 4], f, a)
    a.set_title('Hyp Pos')

def plot_hyp_neg(a):
    f = lambda x: (x[0] - x[1])**2 / (x[0]**2 + x[1]**2)
    plot_function_2d([-4, 4], [-4, 4], f, a)
    a.set_title('Hyp Neg')


def plot_func(a):
    f = lambda x: x[0]**4 + x[1]**4 + x[0]**2 * x[1]**2 -2*x[0]**3 * x[1] - 2*x[0]*x[1]**3 + 2*x[0]**2 * x[1] \
        + 2*x[0]*x[1]**2 - x[0]**3 - x[1]**3 - x[0]*x[1]
    #f = lambda x: 2*x[0]**2 * x[1] - 2*x[0]**3 * x[1] + 2*x[0]*x[1]**2 - 2*x[0]*x[1]**3 + x[0]**2 * x[1]**2 - x[0]*x[1]
    #f = lambda x: x[0]**4 - x[0]**3 - 2*x[0]**3 * x[1] + 2*x[0]**2 * x[1] + .5*(x[0]**2 * x[1]**2 - x[0]*x[1])
    f = lambda x: x[0]**4 - x[0]**3 + x[1]**4 - x[1]**3  + 2*x[0]**2 * x[1]**2 + \
                  x[0]**2 *x[1] + x[0]*x[1]**2 - 2*x[0]**3 *x[1] - 2*x[1]**3 * x[0]
    plot_function_2d([0,1], [0,1], f, a)
    a.set_title('weird func')




if __name__ == '__main__':
    #f, axarr = plt.subplots(1, 1)
    #plot_func(axarr)
    xrange = (-100,100)
    yrange = xrange
    n_samples = 1000.0
    x = np.arange(xrange[0], xrange[1], (xrange[1] - xrange[0]) / n_samples)
    y = np.arange(yrange[0], yrange[1], (yrange[1] - yrange[0]) / n_samples)
    X, Y = np.meshgrid(x, y)
    import math
    pdf = lambda x: (1/math.sqrt(2.0*math.pi))*np.exp(-x**2 / 2)
    pdf_x = pdf(X)
    pdf_y = pdf(Y)
    pdf_x /= pdf_x.sum()
    pdf_y /= pdf_y.sum()
    vals = X*Y/(X**2 + Y**2)


    f, axarr = plt.subplots(2, 2)
    plot_pairwise_contour(axarr[0,0])
    plot_bound(axarr[1,0])
    plot_similar_contour(axarr[0,1])
    plot_neighbor_contour(axarr[1,1])

    '''
    f, axarr = plt.subplots(1, 2)
    plot_hyp_pos(axarr[0])
    plot_hyp_neg(axarr[1])
    '''
    f.tight_layout()
    plt.show()
