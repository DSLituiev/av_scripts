#!/usr/bin/python
import sys;
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
	raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import fileProcessing as fp;
import profileSequences_function;
import util;

def main():
	parser = argparse.ArgumentParser(description="Profiles the sequences");
	parser.add_argument('inputFile');
	parser.add_argument('--outputFile',help="If not specified, name will be 'profiledDifferences_inputFile'");
	parser.add_argument('--significanceThreshold',type=float,default=0.01);
	parser.add_argument('--progressUpdates',type=int);
	parser.add_argument('--hasNoTitle',action="store_true");
	parser.add_argument('--groupByColIndex',type=int,default=0);
	parser.add_argument('--sequencesColIndex',type=int,default=2);
	parser.add_argument('--baseCount', action='store_true');
	parser.add_argument('--gcContent', action='store_true');
	parser.add_argument('--lowercase', action='store_true');
	parser.add_argument('--kmer', type=int);
	args = parser.parse_args();
	profileSequences(args);	

def profileSequences(args):
	countProfilerFactories = [];
	if (args.kmer is not None):
		countProfilerFactories.append(KmerCountProfiler(lambda x: x.upper()), args.kmer);
	if (args.lowercase):
		countProfilerFactories.append(getLowercaseCountProfilerFactory());
	if (args.gcContent):
		countProfilerFactories.append(getGcCountProfilerFactory());
	if (args.baseCount):
		countProfilerFactories.append(getBaseCountProfilerFactory());

	significantDifferences = profileSequences_function.profileInputFile(
		fp.getFileHandle(args.inputFile)
		, countProfilerFactories
		, significanceThreshold
		, preprocessing = util.chainFunctions(fp.trimNewline,fp.splitByTabs)
		, categoryFromInput = lambda x: x[args.groupByColIndex]
		, sequenceFromInput = lambda x: x[args.sequencesColIndex]
		, progressUpdates = args.progressUpdates
		, ignoreInputTitle = not (args.hasNoTitle)

	);
	
	toPrint = "";
	for category in significantDifferences:
		toPrint = toPrint + "-----\n" + category + ":\n-----";
		toPrint = toPrint + "\n".join(significantDifferences[category]);
	
	if (args.outputFile is None):
		args.outputFile = fp.getFileNameParts(args.inputFile).getFilePathWithTransformation(lambda x: 'profiledDifferences_'+x, '.txt');
		
	fp.writeToFile(args.outputFile, toPrint);
	

main();

