#!/usr/bin/env python
from __future__ import print_function
import yaml;
import sys, os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR to point to the av_scripts repo");
sys.path.insert(0,scriptsDir);
import importDataPackage.importData as importData;
    
def testImportData(options):
    yamlObjects = [yaml.load(open(x)) for x in options.yamls];
    splitNameToInputData = importData.getSplitNameToInputDataFromSeriesOfYamls(yamlObjects);
    for splitName in splitNameToInputData.keys():
        split = splitNameToInputData[splitName] 
        print("splitName",splitName)
        print("ids",split.ids);
        print("X",split.X);
        print("Y",split.Y);
        print("labelNames",split.labelNames);
        print("weights",split.weights)
      

if __name__ == "__main__":
    import argparse;
    parser = argparse.ArgumentParser();
    parser.add_argument("--yamls", nargs="+", required=True);
    options = parser.parse_args();
    testImportData(options); 
