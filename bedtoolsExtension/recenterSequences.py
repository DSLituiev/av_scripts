#!/usr/bin/env python
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
    """
        Assuming start and end are chromosomal
        coordinates, returns the coordinates for a region
        of length 'length' centered around the center.
    """
    range = getRange(end-start, length);
    return (start + range[0], start + range[1]);

def getRange(lengthOfInput, lengthOfOutput):
    """
        Return the start and end indices (relative to
        the beginning, 0) for a region of length
        lengthOfOutput centered around lengthOfInput.
    """
    halfLength = int(lengthOfOutput/2);
    remainingLength = lengthOfOutput-halfLength;
    midpoint = int(lengthOfInput/2);
    return (midpoint-halfLength, midpoint+remainingLength); 

def outputFileFromInputFile(inputFile, options):
    return fp.getFileNameParts(inputFile).getFilePathWithTransformation(transformation=lambda x: 'sequencesCentered-'+str(options.sequencesLength)+'_'+x);

def outputTitle(options,sep="\t"):
    toReturn="chrom";
    toReturn+=sep+"cluster";
    toReturn+=sep+"sequence";
    toReturn += "\n";
    return toReturn; 

def recenterSequences(options):
    chromSizes = None;
    if (options.chromSizesFile is not None):
        chromSizes = util.readInChromSizes(options.chromSizesFile);
    if (options.outputFile is not None): #if output file is not inp file dependent...
        outputFileHandle = fp.getFileHandle(options.outputFile, 'w');
        outputFileHandle.close(); #just create the file. Elsewhere append.
    for inputFile in options.inputFiles:
        coreInputFileName = fp.getFileNameParts(inputFile).coreFileName;
        options.outputFile = options.outputFile if (options.outputFile is not None) else outputFileFromInputFile(inputFile, options);
        outputFileHandle = fp.getFileHandle(options.outputFile, 'a');
        def action(inp, lineNumber):
            arrToPrint = [];
            arrToPrint.extend([inp[x] for x in options.auxillaryColumnsBefore]);
            chrom = inp[options.chromColIndex];
            origStart = inp[options.startColIndex];
            origEnd = inp[options.endColIndex];
            summitOffset = None if options.summitOffsetColIndex is None else int(inp[options.summitOffsetColIndex]);
            #chrom = inp[options.chromIdColForIdGen];
            if (summitOffset is None):
                (startBase, endBase) = getRegionCenteredAround(int(origStart), int(origEnd), options.sequencesLength);
            else:
                assert options.sequencesLength%2 == 0;
                halfWindow = options.sequencesLength/2;
                center = (int(origStart)+summitOffset)
                (startBase, endBase) = (center-halfWindow, center+halfWindow) 
            linePasses = True;
            if (startBase < 0):
                linePasses = False;
                print "Dropping",chrom,origStart,origEnd,"because",startBase,"< 0";
            if (chromSizes is not None):
                if chrom not in chromSizes:
                    raise RuntimeError("chromosome "+chrom+" not present in chromSizes file");
                chromEnd = chromSizes[chrom];
                if (endBase > chromEnd):
                    linePasses = False;
                    print "Dropping ",chrom,origStart,origEnd,"because",endBase,">",chromEnd;
            if (linePasses):  
                arrToPrint.extend([str(startBase), str(endBase)]);
                #arrToPrint.append(chrom+":"+startBase+"-"+endBase);
                arrToPrint.extend([inp[x] for x in options.auxillaryColumnsAfter]);
                chromStartEnd = util.makeChromStartEnd(chrom, origStart, origEnd);
                if (options.nameFieldCol4):
                    arrToPrint.append(chromStartEnd);
                    arrToPrint.append(coreInputFileName);
                else:
                    arrToPrint.append(coreInputFileName);
                    arrToPrint.append(chromStartEnd);
                outputFileHandle.write(("\t".join(arrToPrint))+"\n");
        
        fp.performActionOnEachLineOfFile(
            fp.getFileHandle(inputFile)
            , transformation = util.chainFunctions(fp.trimNewline, fp.splitByTabs)
            , action = action
            , ignoreInputTitle = options.titlePresent
        );
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser("For getting the central n bp of a sequence. Dynamically generates output file names for each input file, if not specified. Otherwise, will put sequences from all input files into one output file. In that case, will keep track of the originating file");
    parser.add_argument('inputFiles', nargs='+');
    parser.add_argument('--titlePresent', action="store_true");
    parser.add_argument('--nameFieldCol4', action="store_true");
    parser.add_argument('--outputFile', help="if not supplied, output will be named as input file with 'sequencesCentered-size_' prefixed");
    parser.add_argument('--progressUpdate', type=int, default=10000);
    parser.add_argument('--sequencesLength', required=True, type=int, help="Region of this size centered on the center will be extracted");
    parser.add_argument('--chromSizesFile', help="Optional. First col chrom, second col sizes. If supplied, regions that are going beyond the specified length of the chromosome will be dropped. Assumed to have title.");
    parser.add_argument('--auxillaryColumnsBefore', default=[0]);
    parser.add_argument('--auxillaryColumnsAfter', default=[]);
    parser.add_argument('--chromColIndex', type=int, default=0);
    parser.add_argument('--startColIndex', type=int, default=1);
    parser.add_argument('--endColIndex', type=int, default=2);
    parser.add_argument('--summitOffsetColIndex', type=int, help="Optional. Use if you have a summit position column");
    #parser.add_argument('--chromIdColForIdGen', default=0);
    args = parser.parse_args();    
    recenterSequences(args);
