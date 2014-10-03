#!/srv/gs1/software/python/python-2.7/bin/python
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
	raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
import sys;
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import plottingUtilities as pu;

def main():
	parser = argparse.ArgumentParser(description="Generate histogram of numbers in input file."
				, parents=[pu.getPlotOptionsArgumentParser()]);
	parser.add_argument('inputFile', help='one number per row. Read in as floats.');
	parser.add_argument('--outputPath', help="if not supplied, output will be named as input file with 'shuffled' prefix");
	parser.add_argument('--progressUpdates', help="If set, will get a progress message every so many lines", type=int);
	args = parser.parse_args();
	pu.fileToHistogram(
		args.inputFile
		, outputPath=args.outputPath
		, plotOptions=args
		, progressUpdates=args.progressUpdates);
main();

