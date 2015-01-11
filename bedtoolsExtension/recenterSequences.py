#!/usr/bin/python
import os;
scriptsDir = os.environ.get("UTIL_SCRIPTS_DIR");
if (scriptsDir is None):
    raise Exception("Please set environment variable UTIL_SCRIPTS_DIR");
import sys;
sys.path.insert(0,scriptsDir);
import pathSetter;
import argparse;
import fileProcessing as fp;
import util;

def getRegionCenteredAround(start, end, length):
    range = getRange(end-start, length);
    return (start + range[0], start + range[1]);

def getRange(lengthOfInput, lengthOfOutput):
    halfLength = int(lengthOfOutput/2);
    remainingLength = lengthOfOutput-halfLength;
    midpoint = int(lengthOfInput/2);
    return (midpoint-halfLength, midpoint+remainingLength); 

def outputFileFromInputFile(inputFile):
    return fp.getFileNameParts(inputFile).getFilePathWithTransformation(transformation=lambda x: 'sequencesCentered-'+str(options.sequencesLength)+'_'+x);

def outputTitle(options,sep="\t"):
    toReturn="chrom";
    toReturn+=sep+"cluster";
    toReturn+=sep+"sequence";
    toReturn += "\n";
    return toReturn;

def recenterSequences(options):
    outputFileHandle = fp.getFileHandle(options.outputFile, 'w');
    outputFileHandle.close();
    for inputFile in options.inputFiles:
        options.outputFile = options.outputFile if (options.outputFile is not None) else outputFileFromInputFile(inputFile);
        outputFileHandle = fp.getFileHandle(options.outputFile, 'a');
        def action(inp, lineNumber):
            arrToPrint = [];
            arrToPrint.extend([inp[x] for x in options.auxillaryColumnsBefore]);
            (startBase, endBase) = getRegionCenteredAround(int(inp[options.startColIndex]), int(inp[options.endColIndex]), options.sequencesLength);
            arrToPrint.extend([str(startBase), str(endBase)]);
            arrToPrint.extend([inp[x] for x in options.auxillaryColumnsAfter]);
            outputFileHandle.write(("\t".join(arrToPrint))+"\n");
        
        fp.performActionOnEachLineOfFile(
            fp.getFileHandle(inputFile)
            , transformation = util.chainFunctions(fp.trimNewline, fp.splitByTabs)
            , action = action
            , ignoreInputTitle = False
        );
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser();
    parser.add_argument('inputFiles', nargs='+');
    parser.add_argument('--outputFile', help="if not supplied, output will be named as input file with 'sequencesCentered-size_' prefixed");
    parser.add_argument('--progressUpdates', type=int, default=10000);
    parser.add_argument('--sequencesLength', default=150, type=int, help="Region of this size centered on the center will be extracted");
    parser.add_argument('--auxillaryColumnsBefore', default=[0]);
    parser.add_argument('--auxillaryColumnsAfter', default=[]);
    parser.add_argument('--startColIndex',default=1);
    parser.add_argument('--endColIndex', default=2);
    args = parser.parse_args();    
    recenterSequences(args);
