import matplotlib.pyplot as plt;
import sys;
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
	raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import util;
import fileProcessing as fp;
import argparse;
import matplotlib.pyplot as plt
import numpy as np;

#an attempt to make matplotlib somewhat as easy as R.
def plotHeatmap(data, logTransform=False, zeroCenter=False, cmap=plt.cm.coolwarm):
    fig, ax = plt.subplots()
    plotHeatmapGivenAx(ax, data, logTransform, zeroCenter, cmap);
    return plt;

def plotHeatmapGivenAx(ax, data, logTransform=False, zeroCenter=False, cmap=plt.cm.coolwarm):
    if logTransform:
        data = np.log(np.abs(data)+1)*np.sign(data);
    if (zeroCenter):
        data = data*((data<0)/np.abs(np.min(data)) + (data>0)/np.max(data));
    ax.pcolor(data, cmap=cmap);
    return ax;

def barplot(data):
    plt.bar(np.arange(len(data)), data)
    return plt;

